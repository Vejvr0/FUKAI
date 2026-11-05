from __future__ import annotations
from dataclasses import fields
from PyQt6.QtCore import QObject
from core.gguf import read_meta
from core.settings import ModelMeta
from core.errors import FukaiError, Notice
from storage.database import Database
from ui.settings_store import SettingsStore

__all__ = ["ModelLibrary"]

_META_KEYS = frozenset(f.name for f in fields(ModelMeta))

class ModelLibrary(QObject):
    def __init__(self, settings: SettingsStore, database: Database, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._database = database
    
    
    def models(self) -> list[dict]:
        models_dir = self._settings.current.models_dir
        rows = self._database.list_models()
        for row in rows:
            try:
                row["size_mb"] = (models_dir / row["path"]).stat().st_size / (1024 * 1024)
            except OSError:
                row["size_mb"] = None
        return rows
    
    
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