from __future__ import annotations
from pathlib import Path
from PyQt6.QtWidgets import (
    QFileDialog, QMainWindow, QFrame, QLabel, QHBoxLayout, QVBoxLayout, QStackedWidget, QWidget
)
from PyQt6.QtCore import Qt
from core.constants import APP_NAME
from core.hardware import HardwareProfile
from core.errors import FukaiError, Notice
from storage.database import Database
from ui.chat_controller import ChatController
from ui.chat_view import ChatView
from ui.sidebar import Sidebar, PAGE_CHAT
from ui.constants import WINDOW_MIN_SIZE, WINDOW_SIZE, PANEL_MARGIN
from ui.formatting import size_text
from ui.model_library import ModelLibrary
from ui.settings_store import SettingsStore
from ui.toast import Toast, ToastHost

__all__ = ["MainWindow"]


class MainWindow(QMainWindow):
    def __init__(self, settings: SettingsStore, hardware: HardwareProfile, database: Database,
                 controller: ChatController, library: ModelLibrary) -> None:
        super().__init__()
        self._controller = controller
        self._loading_toast: Toast | None = None
        self._import_toast: Toast | None = None
        self._library = library
        self._settings = settings
        self._hardware = hardware
        self._database = database
        self._chats: dict[int, dict] = {}
        
        self.setWindowTitle(APP_NAME)
        self.resize(*WINDOW_SIZE)
        self.setMinimumSize(*WINDOW_MIN_SIZE)
        
        self._sidebar = Sidebar()
        self._chat = ChatView(hardware)
        
        self._pages = QStackedWidget()
        self._pages.addWidget(self._chat)
        self._pages.addWidget(self._placeholder("Vlastnosti chatu"))
        self._pages.addWidget(self._placeholder("Nastavenia aplikácie"))
        
        panel = QFrame()
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(self._pages)
        
        right = QVBoxLayout()
        right.setContentsMargins(PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN)
        right.addWidget(panel)
        
        central = QWidget()
        central.setObjectName("central")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._sidebar)
        layout.addLayout(right, 1)
        self.setCentralWidget(central)
        
        self._sidebar.page_changed.connect(self._pages.setCurrentIndex)
        self._sidebar.new_chat_request.connect(controller.new_chat)
        self._sidebar.chat_selected.connect(controller.open_chat)
        controller.chat_opened.connect(self._on_chat_opened)
        controller.chats_changed.connect(self._on_chats_changed)
        controller.notice.connect(self.show_notice)
        controller.loading_started.connect(self._on_loading_started)
        controller.loading_finished.connect(self._on_loading_finished)
        
        composer = self._chat.composer
        composer.set_model_source(library.models)
        composer.send_requested.connect(controller.send)
        composer.stop_requested.connect(controller.stop)
        composer.model_selected.connect(controller.select_model)
        controller.busy_changed.connect(composer.set_busy)
        controller.model_changed.connect(composer.set_model)
        controller.turn_started.connect(composer.begin_turn)
        controller.turn_finished.connect(composer.end_turn)
        controller.turn_rolled_back.connect(composer.roll_back)
        controller.loading_started.connect(lambda _title: composer.set_loading(True))
        controller.loading_finished.connect(lambda: composer.set_loading(False))
        
        composer.add_model_requested.connect(self._on_add_model)
        library.import_progress.connect(self._on_import_progress)
        library.import_finished.connect(self._on_import_finished)
        library.import_failed.connect(self._on_import_failed)
        library.import_cancelled.connect(self._on_import_cancelled)
        
        self._toast = ToastHost(self)
        self.apply_theme(settings.current.theme)
        self.reload_chats()
        controller.new_chat()                   # štart = prázdny chat s posledným modelom
        

    @staticmethod
    def _placeholder(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("placeholder")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label
    
    
    def apply_theme(self, theme: str) -> None:
        self._sidebar.set_theme(theme)
        self._chat.set_theme(theme)
        
    
    def reload_chats(self) -> None:
        chats = self._database.list_chats()
        self._chats = {chat["id"]: chat for chat in chats}
        self._sidebar.set_chats(chats)
    
           
    def show_notice(self, notice: Notice, *, persistent: bool = False, progress: bool = False) -> Toast:
        return self._toast.show_notice(notice, persistent=persistent, progress=progress)
    
    
    def _show_page(self, page: int) -> None:
        self._sidebar.show_page(page)
        self._pages.setCurrentIndex(page)
    
    
    def _on_chat_opened(self, chat_id: int | None, title: str, messages: list[dict]) -> None:
        self._sidebar.select_chat(chat_id)
        self._chat.set_title(title)
        self._chat.composer.end_turn()          # bežiaci ťah tohto chatu controller hneď ohlási znova
        self._show_page(PAGE_CHAT)              # správy vykreslí ChatView v ďalšom kúsku
        self._chat.composer.focus_input()


    def _on_chats_changed(self, selected: int | None) -> None:
        self.reload_chats()
        self._sidebar.select_chat(selected)
        if selected is not None and selected == self._controller.chat_id:
            self._chat.set_title(self._chats[selected]["title"])     # nový chat dostal názov


    def _on_loading_started(self, model_title: str) -> None:
        notice = Notice.info("Načítavam model…", hint=f"{model_title} – prvé načítanie môže trvať aj desiatky sekúnd.")
        self._loading_toast = self.show_notice(notice, persistent=True)


    def _on_loading_finished(self) -> None:
        if self._loading_toast is not None:
            self._loading_toast.dismiss()       # neškodné, aj keď ho používateľ zavrel ✕
            self._loading_toast = None
    
    
    
    # --- import modelu ---------------------------------------------------------------------
    
    def _on_add_model(self) -> None:
        if self._library.importing:
            self.show_notice(Notice.info("Import modelu už prebieha.",
                                         hint="Počkaj, kým sa dokončí, alebo ho zruš krížikom v jeho hlásení."))
            return
        path, _ = QFileDialog.getOpenFileName(self, "Pridať model", str(Path.home()), "Modely GGUF (*.gguf)")
        if path:
            self.import_model(Path(path))
    
    
    def import_model(self, source: Path) -> None:
        """Bez dialógu – volá ho `_on_add_model` a testy."""
        try:
            existing = self._library.start_import(source)
        except FukaiError as exc:
            self.show_notice(exc.as_notice())
            return
        if existing is not None:
            self.show_notice(Notice.info("Tento model už v knižnici je.", hint=source.stem))
            self._select_imported(existing)
            return
        notice = Notice.info(f"Importujem {source.stem}", hint="Pripravujem kópiu…")
        self._import_toast = self.show_notice(notice, progress=True)
        self._import_toast.closed.connect(self._on_import_toast_closed)
    
    
    def _on_import_toast_closed(self, _toast: Toast) -> None:
        # ✕ = zrušiť import. Po dokončení toast zatvára _close_import_toast – vtedy už nič nebeží
        # a cancel_import() nič nespraví.
        self._import_toast = None
        self._library.cancel_import()
    
    
    def _on_import_progress(self, copied: int, total: int) -> None:
        if self._import_toast is not None:
            mb = 1024 * 1024
            self._import_toast.set_progress(copied / total if total else 1.0,
                                            f"{size_text(copied / mb)} z {size_text(total / mb)}")
    
    
    def _close_import_toast(self) -> None:
        toast, self._import_toast = self._import_toast, None
        if toast is not None:
            toast.dismiss()
    
    
    def _on_import_finished(self, model_id: int, title: str) -> None:
        self._close_import_toast()
        self.show_notice(Notice.info("Model je pridaný do knižnice.", hint=title))
        self._select_imported(model_id)
    
    
    def _on_import_failed(self, error: FukaiError) -> None:
        self._close_import_toast()
        self.show_notice(error.as_notice())
    
    
    def _on_import_cancelled(self) -> None:
        self._close_import_toast()
        self.show_notice(Notice.info("Import modelu bol zrušený."))
    
    
    def _select_imported(self, model_id: int) -> None:
        """Importovaný model sa rovno vyberie (rozhodnutie autora) – okrem chvíle, keď beží
        odpoveď: model sa vtedy meniť nedá (§7.2 bod 6), v menu už je."""
        if not self._controller.busy:
            self._controller.select_model(model_id)
