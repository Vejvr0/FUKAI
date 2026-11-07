from __future__ import annotations
import sys
import time
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from core.paths import ensure_dir
from core.app_settings import load_settings
from core.constants import APP_NAME, APP_VERSION
from core.hardware import HardwareProfile, check_cores, check_gpu, check_os, check_ram, detect
from core.llm_engine import probe_engine
from core.monitor import UsageMonitor
from core.errors import ConfigError, FukaiError, Notice
from storage.database import Database
from ui.chat_controller import ChatController
from ui.model_library import ModelLibrary
from ui.settings_store import SettingsStore
from ui.llm_service import LlmService
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
        self.setStyle("Fusion")
        self.setApplicationName(APP_NAME)
        self.setApplicationVersion(APP_VERSION)
        icon = ICNS if sys.platform == "darwin" else ICO
        self.setWindowIcon(QIcon(str(icon)))
        
        self.settings: SettingsStore | None = None
        self.hardware: HardwareProfile | None = None
        self.database: Database | None = None
        self.llm: LlmService | None = None
        self.chat: ChatController | None = None
        self.library: ModelLibrary | None = None
        self.monitor: UsageMonitor | None = None
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
        
        self.llm = LlmService()
        self.setStyleSheet(stylesheet(self.settings.current.theme))
        self.chat = ChatController(self.settings, self.hardware, self.database, self.llm)
        self.monitor = UsageMonitor(self.hardware)
        self.window = MainWindow(self.settings, self.hardware, self.database, self.chat, self.library, self.monitor)
        self.window.theme_changed.connect(self._set_theme)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        QTimer.singleShot(max(0, SPLASH_TIME - elapsed_ms), lambda: self._show_main(splash))
        return self.exec()
    
    
    def _startup(self, splash: SplashScreen) -> None:
        self._step(splash, "Načítavam nastavenia...")
        settings, notices = load_settings()
        self.settings = SettingsStore(settings)
        self.notices.extend(notices)
        
        self._step(splash, "Spúšťam engine...")
        engine = probe_engine()
        print(f"[INFO] llama-cpp-python: {engine.version}, GPU offload: {engine.gpu_offload}", file=sys.stderr)
        
        self._step(splash, "Analyzujem hardvér...")
        self.hardware = detect(gpu_offload=engine.gpu_offload)
        for check in (check_os, check_cores, check_ram, check_gpu):
            notice = check(self.hardware)
            if notice is not None:
                self.notices.append(notice)
                
        self._step(splash, "Otváram databázu...")
        self.database = Database()
        self.database.connect()
        
        self._step(splash, "Kontrolujem modely...")
        self._ensure_models_dir()
        self.library = ModelLibrary(self.settings, self.database)
        if self.database.created:
            self._forget_last_model()
        self.notices.extend(self.library.scan_folder())
        self.notices.extend(self.library.refresh_meta())
        
        self._step(splash, f"Pripravené · {self.hardware.backend.upper()}")


    def _ensure_models_dir(self) -> None:
        path = self.settings.current.models_dir
        try:
            ensure_dir(path)
        except OSError as exc:
            raise ConfigError(
                f"{type(exc).__name__}: {exc} ({path})",
                message="Priečinok s modelmi sa nepodarilo vytvoriť.",
                hint="Skontroluj miesto na disku a práva na zápis; cesta je v settings.json."
            ) from exc
    
    
    def _forget_last_model(self) -> None:
        if self.settings.current.last_model_id is None:
            return
        try:
            self.settings.update(last_model_id=None)
        except ConfigError as exc:
            self.notices.append(exc.as_notice())
    
    
    def _step(self, splash: SplashScreen, text: str) -> None:
        splash.showMessage(text)
        self.processEvents()
        
    
    def _show_main(self, splash: SplashScreen) -> None:
        self.window.show()
        splash.finish(self.window)
        QTimer.singleShot(0, self._report_notices)


    def _set_theme(self, theme: str) -> None:
        self.setStyleSheet(stylesheet(theme))
        self.window.apply_theme(theme)
    
    
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
        if self.llm is not None:
            self.llm.shutdown()
            self.llm = None
        if self.library is not None:
            self.library.shutdown()
        if self.monitor is not None:
            self.monitor.close()
            self.monitor = None
        if self.database is not None:
            self.database.close()
            self.database = None
