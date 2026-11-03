from __future__ import annotations
from PyQt6.QtWidgets import (
    QMainWindow, QFrame, QLabel, QHBoxLayout, QVBoxLayout, QStackedWidget, QWidget
)
from PyQt6.QtCore import Qt
from core.app_settings import AppSettings
from core.constants import APP_NAME
from core.hardware import HardwareProfile
from core.errors import Notice
from storage.database import Database
from ui.chat_view import ChatView
from ui.sidebar import Sidebar, PAGE_CHAT
from ui.constants import WINDOW_MIN_SIZE, WINDOW_SIZE, PANEL_MARGIN
from ui.toast import ToastHost

__all__ = ["MainWindow"]


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings, hardware: HardwareProfile, database: Database) -> None:
        super().__init__()
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
        self._sidebar.new_chat_request.connect(self._new_chat)
        self._sidebar.chat_selected.connect(self._open_chat)
        
        self._toast = ToastHost(self)
        self.apply_theme(settings.theme)
        self.reload_chats()
        

    @staticmethod
    def _placeholder(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("placeholder")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label
    
    
    def apply_theme(self, theme: str) -> None:
        self._sidebar.set_theme(theme)
        
    
    def reload_chats(self) -> None:
        chats = self._database.list_chats()
        self._chats = {chat["id"]: chat for chat in chats}
        self._sidebar.set_chats(chats)
    
           
    def show_notice(self, notice: Notice) -> None:
        self._toast.show_notice(notice)
    
    
    def _show_page(self, page: int) -> None:
        self._sidebar.show_page(page)
        self._pages.setCurrentIndex(page)
    
    
    def _new_chat(self) -> None:
        self._sidebar.select_chat(None)
        self._chat.set_title("Nový chat")
        self._show_page(PAGE_CHAT)
    
    
    def _open_chat(self, chat_id: int) -> None:
        self._chat.set_title(self._chats[chat_id]["title"])
        self._show_page(PAGE_CHAT)
    
