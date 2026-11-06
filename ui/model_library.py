from __future__ import annotations
import sys
import shutil
import threading
from dataclasses import fields
from pathlib import Path
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from core.constants import GGUF_SUFFIX, IMPORT_FREE_MARGIN_MB
from core.gguf import check_usable, read_meta
from core.settings import ModelMeta
from core.errors import FukaiError, ModelError, ModelImportError, Notice, StorageError
from storage.database import Database
from ui.formatting import size_text
from ui.settings_store import SettingsStore
from ui.workers import ImportRequest, ImportWorker

__all__ = ["ModelLibrary"]

_META_KEYS = frozenset(f.name for f in fields(ModelMeta))
_MB = 1024 * 1024


class ModelLibrary(QObject):
    _import_requested = pyqtSignal(object)
    
    import_progress = pyqtSignal("qint64", "qint64")
    import_finished = pyqtSignal(int, str)
    import_failed = pyqtSignal(object)
    import_cancelled = pyqtSignal()
    
    
    def __init__(self, settings: SettingsStore, database: Database, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._database = database
        self._thread: QThread | None = None
        self._worker: ImportWorker | None = None
        self._cancel: threading.Event | None = None
    
    
    def models(self) -> list[dict]:
        models_dir = self._settings.current.models_dir
        rows = self._database.list_models()
        for row in rows:
            try:
                row["size_mb"] = (models_dir / row["path"]).stat().st_size / (1024 * 1024)
            except OSError:
                row["size_mb"] = None
        return rows
    
    
    def model_path(self, model: dict) -> Path:
        return self._settings.current.models_dir / model["path"]
    
    
    def delete_model(self, model_id: int) -> None:
        model = self._database.get_model(model_id)
        if model is None:
            return
        path = self.model_path(model)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise ModelError(
                f"{type(exc).__name__}: {exc}",
                message="Súbor modelu sa nepodarilo zmazať.",
                hint=f"{path} - možno ho používa iný program. Zatvor ho a skús to znova."
            ) from exc
        self._database.delete_model(model_id)
    
    
    def scan_folder(self) -> list[Notice]:
        models_dir = self._settings.current.models_dir
        try:
            entries = sorted(models_dir.iterdir())
        except OSError as exc:
            return [Notice.warning(
                "Priečinok s modelmi sa nedá prečítať.",
                hint=str(models_dir),
                detail=f"{type(exc).__name__}: {exc}"
            )]
        known = {row["path"] for row in self._database.list_models()}
        added = []
        for path in entries:
            if path.name in known or path.suffix.lower() != GGUF_SUFFIX or not path.is_file():
                continue
            try:
                meta = read_meta(path)
                check_usable(meta)
            except ModelError as exc:
                print(f"[SKEN] preskočený {path.name}: {exc.message} | {exc}", file=sys.stderr)
                continue
            try:
                self._database.add_model(path.stem, path.name, meta.to_dict())
            except StorageError as exc:
                return [*self._added_notice(added), exc.as_notice()]
            added.append(path.stem)
        return self._added_notice(added)

    
    @staticmethod
    def _added_notice(added: list[str]) -> list[Notice]:
        if not added:
            return []
        return [Notice.info(f"Z priečinka modelov pribudli do zoznamu: {len(added)}", hint=", ".join(added))]
    
    
    def refresh_meta(self) -> list[Notice]:
        notices = []
        models_dir = self._settings.current.models_dir
        for row in self._database.list_models():
            if _META_KEYS <= row["meta"].keys():
                continue
            path = models_dir / row["path"]
            if not path.is_file():
                continue
            try:
                self._database.set_model_meta(row["id"], read_meta(path).to_dict())
            except FukaiError as exc:
                notices.append(Notice.warning(
                    f"Údaje o modeli „{row['title']}“ sa nepodarilo prečítať.",
                    hint="Súbor môže byť poškodený. Ak sa model nenačíta, odstráň ho a importuj znova.",
                    detail=f"{type(exc).__name__}: {exc}"
                ))
        return notices
    
    
    @property
    def importing(self) -> bool:
        return self._cancel is not None
    
    
    def start_import(self, source: Path) -> int | None:
        if self.importing:
            raise RuntimeError("import už beží")
        source = Path(source)
        existing = self.find_duplicate(source)
        if existing is not None:
            return existing
        models_dir = self._settings.current.models_dir
        self._check_space(source, models_dir)
        self._cancel = threading.Event()
        self._ensure_thread()
        self._import_requested.emit(ImportRequest(source, self._free_dest(models_dir, source.name), self._cancel))
        return None
    
    
    def cancel_import(self) -> None:
        if self._cancel is not None:
            self._cancel.set()
    
    
    def find_duplicate(self, source: Path) -> int | None:
        try:
            size = source.stat().st_size
        except OSError:
            return None
        models_dir = self._settings.current.models_dir
        for row in self._database.list_models():
            if row["path"] != source.name:
                continue
            try:
                if (models_dir / row["path"]).stat().st_size == size:
                    return row["id"]
            except OSError:
                continue
        return None
    
    
    def shutdown(self) -> None:
        self.cancel_import()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
    
    
    @staticmethod
    def _check_space(source: Path, models_dir: Path) -> None:
        try:
            size_mb = source.stat().st_size / _MB
            free_mb = shutil.disk_usage(models_dir).free / _MB
        except OSError:
            return
        if free_mb < size_mb + IMPORT_FREE_MARGIN_MB:
            raise ModelImportError(
                f"model {size_mb:.0f} MB, voľné {free_mb:.0f} MB, rezerva {IMPORT_FREE_MARGIN_MB} MB",
                message="Na disku nie je dosť miesta na kópiu modelu.",
                hint=f"Model má {size_text(size_mb)}, voľných je {size_text(free_mb)}. Po importe má zostať aspoň {size_text(IMPORT_FREE_MARGIN_MB)}."
            )
    
    
    def _free_dest(self, models_dir: Path, name: str) -> Path:
        dest = models_dir / name
        stem, suffix = dest.stem, dest.suffix
        number = 2
        while dest.exists():
            dest = models_dir / f"{stem}-{number}{suffix}"
            number += 1
        return dest
    
    
    def _ensure_thread(self) -> None:
        if self._thread is not None:
            return
        self._thread = QThread()
        self._thread.setObjectName("import")
        self._worker = ImportWorker()
        self._worker.moveToThread(self._thread)
        self._import_requested.connect(self._worker.run)
        self._worker.progress.connect(self.import_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.cancelled.connect(self._on_cancelled)
        self._thread.start()
    
    
    def _on_finished(self, dest: Path, meta: ModelMeta) -> None:
        self._cancel = None
        try:
            model_id = self._register(dest, meta)
        except StorageError as exc:
            self.import_failed.emit(exc)
            return
        self.import_finished.emit(model_id, dest.stem)
    
    
    def _register(self, dest: Path, meta: ModelMeta) -> int:
        for row in self._database.list_models():
            if row["path"] == dest.name:
                self._database.set_model_meta(row["id"], meta.to_dict())
                return row["id"]
        return self._database.add_model(dest.stem, dest.name, meta.to_dict())
    
    
    def _on_failed(self, error: FukaiError) -> None:
        self._cancel = None
        self.import_failed.emit(error)
    
    
    def _on_cancelled(self) -> None:
        self._cancel = None
        self.import_cancelled.emit()
        