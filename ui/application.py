from __future__ import annotations
import sys
import time
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from core.app_settings import AppSettings, load_settings
from core.constants import APP_NAME, APP_VERSION
from core.hardware import HardwareProfile, check_cores, check_gpu, check_os, check_ram, detect
from core.errors import FukaiError, Notice
from storage.database import Database
from ui.constants import ICNS, ICO, SPLASH_TIME, WINDOWS_APP_ID
from ui.main_window import MainWindow
from ui.splash import SplashScreen
from ui.style import stylesheet

__all__ = ["Application"]


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except (AttributeError, OSError):
        pass


class Application(QApplication):
    def __init__(self, argv: list[str]) -> None:
        _set_windows_app_id()
        super().__init__(argv)
        self.setApplicationName(APP_NAME)
        self.setApplicationVersion(APP_VERSION)
        icon = ICNS if sys.platform == "darwin" else ICO
        self.setWindowIcon(QIcon(str(icon)))
        
        self.settings: AppSettings | None = None
        self.hardware: HardwareProfile | None = None
        self.database: Database | None = None
        self.notices: list[Notice] = []
        self.window: MainWindow | None = None
        
        self.aboutToQuit.connect(self.shutdown)
        
    
    def run(self) -> int:
        splash = SplashScreen()
        splash.show()
        self.processEvents()
        started = time.monotonic()
        
        try:
            self._startup(splash)
        except FukaiError as exc:
            splash.close()
            self._show_fatal(exc)
            self.shutdown()
            return 1
        
        self.setStyleSheet(stylesheet(self.settings.theme))
        self.window = MainWindow(self.settings, self.hardware, self.database)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        QTimer.singleShot(max(0, SPLASH_TIME - elapsed_ms), lambda: self._show_main(splash))
        return self.exec()
    
    
    def _startup(self, splash: SplashScreen) -> None:
        self._step(splash, "Načítavam nastavenia...")
        self.settings, notices = load_settings()
        self.notices.extend(notices)
        
        self._step(splash, "Analyzujem hardvér...")
        self.hardware = detect()
        for check in (check_os, check_cores, check_ram, check_gpu):
            notice = check(self.hardware)
            if notice is not None:
                self.notices.append(notice)
                
        self._step(splash, "Otváram databázu...")
        self.database = Database()
        self.database.connect()
        
        self._step(splash, f"Pripravené · {self.hardware.backend.upper()}")
        
    
    def _step(self, splash: SplashScreen, text: str) -> None:
        splash.showMessage(text)
        self.processEvents()
        
    
    def _show_main(self, splash: SplashScreen) -> None:
        self.window.show()
        splash.finish(self.window)
        QTimer.singleShot(0, self._report_notices)
    
    
    def _report_notices(self) -> None:
        for notice in self.notices:
            print(notice.log_line(), file=sys.stderr)
            self.window.show_notice(notice)
    
    
    def _show_fatal(self, exc: FukaiError) -> None:
        print(exc.as_notice().log_line(), file=sys.stderr)
        self._message_box(QMessageBox.Icon.Critical, exc.as_notice()).exec()
    
    
    @staticmethod
    def _message_box(icon: QMessageBox.Icon, notice: Notice, parent=None) -> QMessageBox:
        box = QMessageBox(icon, APP_NAME, notice.message, parent=parent)
        if notice.hint:
            box.setInformativeText(notice.hint)
        return box

    
    def shutdown(self) -> None:
        if self.database is not None:
            self.database.close()
            self.database = None
