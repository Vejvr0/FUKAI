from __future__ import annotations
from PyQt6.QtWidgets import (
    QButtonGroup, QFrame, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout
)
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtSvgWidgets import QSvgWidget
from ui.constants import (
    CHAT_ITEM_HEIGHT, HILLS, ICON_SIZE, SIDEBAR_LOGO, SIDEBAR_LOGO_WIDTH, SIDEBAR_WIDTH, ICON_GAP
)
from ui.icons import icon, pixmap
from ui.style import THEMES

__all__ = [
    "Sidebar",
    "PAGE_CHAT",
    "PAGE_PROPERTIES",
    "PAGE_SETTINGS",
]

PAGE_CHAT, PAGE_PROPERTIES, PAGE_SETTINGS = range(3)
TABS = (
    (PAGE_CHAT, "chat", "Chat"),
    (PAGE_PROPERTIES, "brain", "Vlastnosti"),
    (PAGE_SETTINGS, "gear", "Nastavenia")
)
CHAT_ID = Qt.ItemDataRole.UserRole


class Sidebar(QFrame):
    page_changed = pyqtSignal(int)
    new_chat_request = pyqtSignal()
    chat_selected = pyqtSignal(int)
    
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        
        self._logo = QLabel()
        self._logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._tabs = QButtonGroup(self)
        for page, _, text in TABS:
            button = QPushButton(ICON_GAP + text, self)
            button.setObjectName("tab")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
            self._tabs.addButton(button, page)
        self._tabs.button(PAGE_CHAT).setChecked(True)
        self._tabs.idClicked.connect(self.page_changed)
        
        self._new_chat = QPushButton(ICON_GAP + "Fúkni nový chat")
        self._new_chat.setObjectName("newChat")
        self._new_chat.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_chat.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self._new_chat.clicked.connect(self.new_chat_request)
        
        self._list_label = QLabel("Posledné")
        self._list_label.setObjectName("listLabel")
        
        self._list = QListWidget()
        self._list.setObjectName("chatList")
        self._list.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._list.setUniformItemSizes(True)
        self._list.itemClicked.connect(self._on_item_clicked)
        
        hills = QSvgWidget(str(HILLS))
        hills.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        box = hills.renderer().viewBoxF()
        hills.setFixedHeight(round(SIDEBAR_WIDTH * box.height() / box.width()))
        
        top = QVBoxLayout()
        top.setContentsMargins(16, 20, 16, 0)
        top.setSpacing(8)
        top.addWidget(self._logo)
        top.addSpacing(12)
        for button in self._tabs.buttons():
            top.addWidget(button)
        top.addSpacing(8)
        top.addWidget(self._new_chat)
        
        chats = QVBoxLayout()
        chats.setContentsMargins(12, 4 , 12, 0)
        chats.setSpacing(0)
        chats.addWidget(self._list_label)
        chats.addWidget(self._list, 1)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(top)
        layout.addLayout(chats, 1)
        layout.addWidget(hills)
    
    
    def set_theme(self, theme: str) -> None:
        color = THEMES[theme]["side_text"]
        self._logo.setPixmap(pixmap(SIDEBAR_LOGO[theme], SIDEBAR_LOGO_WIDTH))
        for page, icon_name, _ in TABS:
            self._tabs.button(page).setIcon(icon(icon_name, color))
        self._new_chat.setIcon(icon("new", color))
    
    
    def show_page(self, page: int) -> None:
        self._tabs.button(page).setChecked(True)
    
    
    def set_chats(self, chats: list[dict]) -> None:
        self._list.clear()
        for chat in chats:
            item = QListWidgetItem(chat["title"])
            item.setData(CHAT_ID, chat["id"])
            item.setToolTip(chat["title"])
            item .setSizeHint(QSize(0, CHAT_ITEM_HEIGHT))
            self._list.addItem(item)
        self._list_label.setVisible(bool(chats))
    
    
    def select_chat(self, chat_id: int | None) -> None:
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item.data(CHAT_ID) == chat_id:
                self._list.setCurrentItem(item)
                return
        self._list.setCurrentRow(-1)
        self._list.clearSelection()
    
    
    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.chat_selected.emit(item.data(CHAT_ID))