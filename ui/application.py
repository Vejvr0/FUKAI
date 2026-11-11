from __future__ import annotations
import logging
import platform
import sys
import threading
import time
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, QtMsgType, Qt, QTimer, pyqtSignal, qInstallMessageHandler
from PyQt6.QtGui import QIcon
from core.paths import app_dir, ensure_dir
from core.log import enable_crash_log, setup_logging
from core.app_settings import load_settings
from core.constants import APP_NAME, APP_VERSION
from core.hardware import HardwareProfile, check_cores, check_gpu, check_os, check_ram, detect
from core.llm_engine import probe_engine
from core.monitor import UsageMonitor
from core.errors import ConfigError, FukaiError, Notice, Severity
from storage.database import Database
from ui.chat_controller import ChatController
from ui.model_library import ModelLibrary
from ui.settings_store import SettingsStore
from ui.llm_service import LlmService
from ui.web_service import WebService
from ui.attachments import AttachmentService
from ui.constants import (
    ICNS, ICO, LOG_HINT, SPLASH_TIME, UNCAUGHT_HINT, UNCAUGHT_MESSAGE, UNCAUGHT_START_HINT, WINDOWS_APP_ID
)
from ui.main_window import MainWindow
from ui.splash import SplashScreen
from ui.style import stylesheet

__all__ = ["Application"]

log = logging.getLogger(__name__)

_QT_LEVELS = {
    QtMsgType.QtDebugMsg: logging.DEBUG,
    QtMsgType.QtInfoMsg: logging.INFO,
    QtMsgType.QtWarningMsg: logging.WARNING,
    QtMsgType.QtCriticalMsg: logging.ERROR,
    QtMsgType.QtFatalMsg: logging.CRITICAL,
}


def _qt_message(kind: QtMsgType, context, message: str) -> None:
    """Hlásenia Qt (napr. „QThread: Destroyed while thread is still running“) do fukai.log."""
    category = context.category or "qt"
    # qt.qpa.* sú hlásenia platformy - na macOS „propagateSizeHints“ pri každom okne, aliasy písiem.
    if category.startswith("qt.qpa.") and kind in (QtMsgType.QtDebugMsg, QtMsgType.QtInfoMsg, QtMsgType.QtWarningMsg):
        return
    logging.getLogger("ui.qt").log(_QT_LEVELS.get(kind, logging.WARNING), "%s: %s", category, message)


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except (AttributeError, OSError):
        pass


class Application(QApplication):
    _uncaught = pyqtSignal(str)         # neodchytená výnimka → toast v hlavnom vlákne (A3)


    def __init__(self, argv: list[str]) -> None:
        _set_windows_app_id()
        super().__init__(argv)
        # Log ako prvý - aby v ňom bol aj štart. Vlastný súbor, nie stderr: ten počas
        # načítania modelu llama-cpp-python umlčí (§8 krok 9, test na PC 1).
        self.log_path = setup_logging()
        enable_crash_log()
        qInstallMessageHandler(_qt_message)
        self._error_toast = None
        # Vždy cez frontu: výnimka mohla vzniknúť vo workeri, toast sa smie ukázať len v hlavnom vlákne.
        self._uncaught.connect(self._show_uncaught, Qt.ConnectionType.QueuedConnection)
        sys.excepthook = self._on_uncaught
        threading.excepthook = lambda args: self._on_uncaught(args.exc_type, args.exc_value, args.exc_traceback)
        log.info("FUKAI %s · %s · Python %s · Qt %s · PyQt %s · dáta %s", APP_VERSION, platform.platform(),
                 platform.python_version(), QT_VERSION_STR, PYQT_VERSION_STR, app_dir())
        self.setStyle("Fusion")
        self.setApplicationName(APP_NAME)
        self.setApplicationVersion(APP_VERSION)
        icon = ICNS if sys.platform == "darwin" else ICO
        self.setWindowIcon(QIcon(str(icon)))
        
        self.settings: SettingsStore | None = None
        self.hardware: HardwareProfile | None = None
        self.database: Database | None = None
        self.llm: LlmService | None = None
        self.web: WebService | None = None
        self.attachments: AttachmentService | None = None
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
        except Exception:
            # Bez okna sa pokračovať nedá - toast nemá kam ísť, preto fatálny dialóg ako vyššie.
            log.critical("Neočakávaná chyba pri štarte", exc_info=True)
            splash.close()
            self._show_fatal(FukaiError(hint=self._with_log(UNCAUGHT_START_HINT)))
            self.shutdown()
            return 1
        
        self.llm = LlmService()
        self.setStyleSheet(stylesheet(self.settings.current.theme))
        self.web = WebService()
        self.chat = ChatController(self.settings, self.hardware, self.database, self.llm, self.web)
        self.monitor = UsageMonitor(self.hardware)
        self.attachments = AttachmentService()
        self.window = MainWindow(self.settings, self.hardware, self.database, self.chat, self.library, self.monitor, self.attachments)
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
        log.info("llama-cpp-python %s · GPU offload %s", engine.version, engine.gpu_offload)
        
        self._step(splash, "Analyzujem hardvér...")
        self.hardware = detect(gpu_offload=engine.gpu_offload)
        hw, gpu = self.hardware, self.hardware.gpu
        vram = f" · VRAM {gpu.vram_total_mb} MB" if gpu and gpu.vram_total_mb else ""   # Metal VRAM nemá
        log.info("Hardvér: backend %s · %d jadier (%d výkonných) · RAM %d MB · GPU %s%s", hw.backend,
                 hw.cores_logical, hw.cores_performance, hw.ram_total_mb, gpu.name if gpu else "žiadna", vram)
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
            self.window.show_notice(notice)         # zapíše ho do logu
    
    
    def _show_fatal(self, exc: FukaiError) -> None:
        log.error("%s | %s", exc.message, exc.detail or "-")
        self._message_box(QMessageBox.Icon.Critical, exc.as_notice()).exec()
    
    
    @staticmethod
    def _message_box(icon: QMessageBox.Icon, notice: Notice, parent=None) -> QMessageBox:
        box = QMessageBox(icon, APP_NAME, notice.message, parent=parent)
        if notice.hint:
            box.setInformativeText(notice.hint)
        return box

    
    def _on_uncaught(self, exc_type, exc, tb) -> None:
        """A3 - výnimka, ktorú nič neošetrilo: zo slotu, z vlákna aj z hlavného programu.
        S vlastným excepthookom ju PyQt nezmení na abort (kód 134) a appka beží ďalej
        (rozhodnutie autora). Traceback ide do logu, používateľ dostane chybový toast."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        log.critical("Neodchytená výnimka", exc_info=(exc_type, exc, tb))
        self._uncaught.emit(f"{exc_type.__name__}: {exc}")


    def _show_uncaught(self, detail: str) -> None:
        if self.window is None or not self.window.isVisible():
            return          # pri štarte ju rieši run() fatálnym dialógom, pri ukončení už niet kde
        if self._error_toast is not None:
            return          # záplava (chyba v časovači): kým je hlásenie otvorené, ďalšie len do logu
        notice = Notice(Severity.ERROR, UNCAUGHT_MESSAGE, self._with_log(UNCAUGHT_HINT), detail)
        self._error_toast = self.window.show_notice(notice)
        self._error_toast.closed.connect(self._on_error_toast_closed)


    def _on_error_toast_closed(self, *_) -> None:
        self._error_toast = None


    def _with_log(self, hint: str) -> str:
        """Rada + cesta k logu, keď log existuje (setup_logging mohol zlyhať)."""
        return f"{hint} {LOG_HINT.format(path=self.log_path)}" if self.log_path else hint


    def shutdown(self) -> None:
        if self.llm is not None:
            self.llm.shutdown()
            self.llm = None
        if self.library is not None:
            self.library.shutdown()
        if self.monitor is not None:
            self.monitor.close()
            self.monitor = None
        if self.attachments is not None:
            self.attachments.shutdown()
            self.attachments = None
        if self.web is not None:
            self.web.shutdown()
            self.web = None
        if self.database is not None:
            self.database.close()
            self.database = None
