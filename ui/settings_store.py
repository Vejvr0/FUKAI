# --- ./ui/settings_store.py ---


from __future__ import annotations
from dataclasses import replace
from PyQt6.QtCore import QObject, pyqtSignal
from core.app_settings import AppSettings, save_settings

__all__ = ["SettingsStore"]


class SettingsStore(QObject):
    changed = pyqtSignal(object)
    
    
    def __init__(self, settings: AppSettings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
    
    
    @property
    def current(self) -> AppSettings:
        return self._settings

    
    def update(self, **changes) -> None:
        self._settings = replace(self._settings, **changes)
        self.changed.emit(self._settings)
        save_settings(self._settings)
