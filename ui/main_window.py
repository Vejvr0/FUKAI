from __future__ import annotations
from PyQt6.QtWidgets import QMainWindow, QLabel
from PyQt6.QtCore import Qt
from core.app_settings import AppSettings
from core.constants import APP_NAME
from core.hardware import HardwareProfile
from storage.database import Database
from ui.constants import WINDOW_MIN_SIZE, WINDOW_SIZE

__all__ = ["MainWindow"]


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings, hardware: HardwareProfile, database: Database) -> None:
        super().__init__()
        self._settings = settings
        self._hardware = hardware
        self._database = database
        
        self.setWindowTitle(APP_NAME)
        self.resize(*WINDOW_SIZE)
        self.setMinimumSize(*WINDOW_MIN_SIZE)
        
        hw = hardware
        info = QLabel(f"os: {hw.system} | verzia: {hw.release} | backend {hw.backend} | CPU P-cores: {hw.cores_performance} | RAM: {hw.ram_total_mb / 1024:.0f} GB")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(info)
    