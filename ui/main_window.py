from __future__ import annotations
from PyQt6.QtWidgets import (
    QMainWindow, QFrame, QLabel, QHBoxLayout, QVBoxLayout, QStackedWidget, QWidget
)
from PyQt6.QtCore import Qt
from core.constants import APP_NAME
from core.hardware import HardwareProfile
from core.errors import Notice
from storage.database import Database
from ui.chat_controller import ChatController
from ui.chat_view import ChatView
from ui.sidebar import Sidebar, PAGE_CHAT
from ui.constants import WINDOW_MIN_SIZE, WINDOW_SIZE, PANEL_MARGIN
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
    
           
    def show_notice(self, notice: Notice, *, persistent: bool = False) -> Toast:
        return self._toast.show_notice(notice, persistent=persistent)
    
    
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
    
