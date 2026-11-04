from __future__ import annotations
from PyQt6.QtCore import QObject
from storage.database import Database
from ui.settings_store import SettingsStore

__all__ = ["ModelLibrary"]


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