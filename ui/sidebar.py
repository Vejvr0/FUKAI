from __future__ import annotations
from typing import Callable
from PyQt6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu,
    QPushButton, QToolButton, QVBoxLayout, QWidget, QWidgetAction
)
from PyQt6.QtCore import QEvent, QObject, QPoint, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QKeyEvent
from PyQt6.QtSvgWidgets import QSvgWidget
from ui.constants import (
    CHAT_ITEM_HEIGHT, CHAT_ITEM_SPACING, CHAT_MENU_WIDTH, CHAT_ROW_BUTTON, HILLS, ICON_SIZE,
    SIDEBAR_LOGO, SIDEBAR_LOGO_WIDTH, SIDEBAR_WIDTH, ICON_GAP
)
from ui.formatting import tokens_text
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


class _ChatRow(QFrame):
    """Riadok zoznamu chatov. Je to widget v položke (`setItemWidget`), nie kreslený text –
    inak sa doň nedá dať tlačidlo ⋯ ani vstup na premenovanie. Dôsledok: `itemClicked`
    zoznamu sa už nevyšle (widget udalosť spotrebuje, tá istá pasca ako `QWidgetAction`
    v menu modelov), preto vlastný `clicked`."""
    clicked = pyqtSignal()
    menu_requested = pyqtSignal()
    rename_submitted = pyqtSignal(str)


    def __init__(self, title: str, dots: QIcon, check: QIcon, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("chatRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._title = title
        self._editing = False
        self._hover = False
        self._menu_open = False
        self._dots = dots
        self._check = check

        self._label = QLabel()
        self._label.setObjectName("chatTitle")

        self._edit = QLineEdit()
        self._edit.setObjectName("chatEdit")
        self._edit.setFrame(False)
        self._edit.hide()
        self._edit.returnPressed.connect(self._submit)
        self._edit.installEventFilter(self)

        self._button = QToolButton()
        self._button.setObjectName("chatMore")
        self._button.setFixedSize(CHAT_ROW_BUTTON, CHAT_ROW_BUTTON)
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._button.clicked.connect(self._on_button)
        policy = self._button.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self._button.setSizePolicy(policy)

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 0, 4, 0)
        row.setSpacing(4)
        row.addWidget(self._label, 1)
        row.addWidget(self._edit, 1)
        row.addWidget(self._button)

        self._update_button()
        self._apply_title()


    @property
    def title(self) -> str:
        return self._title


    @property
    def editing(self) -> bool:
        return self._editing


    def set_active(self, active: bool) -> None:
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)


    def set_icons(self, dots: QIcon, check: QIcon) -> None:
        self._dots, self._check = dots, check
        self._update_button()


    def set_menu_open(self, open_: bool) -> None:
        """Kým je menu otvorené, myš je mimo riadku – bez tohto by ⋯ zmizlo pod menu."""
        self._menu_open = open_
        self._update_button()


    def begin_edit(self) -> None:
        self._editing = True
        self._edit.setText(self._title)
        self._edit.setSelection(len(self._title), -len(self._title))
        self._label.hide()
        self._edit.show()
        self._edit.setFocus()
        self._update_button()


    def enterEvent(self, event) -> None:
        self._hover = True
        self._update_button()
        super().enterEvent(event)


    def leaveEvent(self, event) -> None:
        self._hover = False
        self._update_button()
        super().leaveEvent(event)


    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_title()


    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._apply_title()


    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._edit and self._editing:
            if event.type() == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
                if event.key() == Qt.Key.Key_Escape:
                    self._end_edit()
                    return True
            elif event.type() == QEvent.Type.FocusOut:
                self._end_edit()
        return False


    def mouseReleaseEvent(self, event) -> None:
        if (not self._editing and event.button() == Qt.MouseButton.LeftButton
                and self.rect().contains(event.position().toPoint())):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


    def _on_button(self) -> None:
        if self._editing:
            self._submit()
        else:
            self.menu_requested.emit()


    def _submit(self) -> None:
        title = self._edit.text().strip()
        changed = bool(title) and title != self._title
        self._end_edit()
        if changed:
            self.rename_submitted.emit(title)


    def _end_edit(self) -> None:
        if not self._editing:
            return
        self._editing = False
        self._edit.hide()
        self._label.show()
        self._update_button()


    def _update_button(self) -> None:
        self._button.setIcon(self._check if self._editing else self._dots)
        self._button.setToolTip("Potvrdiť nový názov" if self._editing else "Možnosti chatu")
        self._button.setVisible(self._editing or self._hover or self._menu_open)


    def _apply_title(self) -> None:
        margins = self.contentsMargins()
        width = (self.width() - margins.left() - margins.right()
                 - CHAT_ROW_BUTTON - self.layout().spacing())
        metrics = self._label.fontMetrics()
        self._label.setText(metrics.elidedText(self._title, Qt.TextElideMode.ElideRight, max(0, width)))


class Sidebar(QFrame):
    page_changed = pyqtSignal(int)
    new_chat_request = pyqtSignal()
    chat_selected = pyqtSignal(int)
    chat_rename_requested = pyqtSignal(int, str)
    chat_delete_requested = pyqtSignal(int)


    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)

        self._theme = "light"
        self._dots = QIcon()
        self._check = QIcon()
        self._rows: dict[int, _ChatRow] = {}
        self._active: int | None = None
        self._token_source: Callable[[int], int] = lambda _chat_id: 0

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
        self._list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._list.setSpacing(CHAT_ITEM_SPACING)
        self._list.setUniformItemSizes(True)

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
        self._theme = theme
        color = THEMES[theme]["side_text"]
        self._logo.setPixmap(pixmap(SIDEBAR_LOGO[theme], SIDEBAR_LOGO_WIDTH))
        for page, icon_name, _ in TABS:
            self._tabs.button(page).setIcon(icon(icon_name, color))
        self._new_chat.setIcon(icon("new", color))
        self._dots = icon("dots", color, 16)
        self._check = icon("check", color, 16)
        for row in self._rows.values():
            row.set_icons(self._dots, self._check)


    def show_page(self, page: int) -> None:
        self._tabs.button(page).setChecked(True)


    def set_token_source(self, source: Callable[[int], int]) -> None:
        self._token_source = source


    def set_chats(self, chats: list[dict]) -> None:
        self._list.clear()
        self._rows.clear()
        for chat in chats:
            chat_id = chat["id"]
            row = _ChatRow(chat["title"], self._dots, self._check)
            row.setToolTip(chat["title"])
            row.clicked.connect(lambda chat_id=chat_id: self.chat_selected.emit(chat_id))
            row.menu_requested.connect(lambda chat_id=chat_id: self._open_chat_menu(chat_id))
            row.rename_submitted.connect(lambda title, chat_id=chat_id: self._rename(chat_id, title))
            item = QListWidgetItem()
            item.setData(CHAT_ID, chat_id)
            item.setSizeHint(QSize(0, CHAT_ITEM_HEIGHT))
            self._list.addItem(item)
            self._list.setItemWidget(item, row)
            self._rows[chat_id] = row
        self._list_label.setVisible(bool(chats))
        self.select_chat(self._active)


    def select_chat(self, chat_id: int | None) -> None:
        self._active = chat_id if chat_id in self._rows else None
        for row_id, row in self._rows.items():
            row.set_active(row_id == self._active)


    def _rename(self, chat_id: int, title: str) -> None:
        QTimer.singleShot(0, lambda: self.chat_rename_requested.emit(chat_id, title))


    def _open_chat_menu(self, chat_id: int) -> None:
        row = self._rows.get(chat_id)
        if row is None:
            return
        tokens = QLabel(tokens_text(self._token_source(chat_id)))
        tokens.setObjectName("menuLabel")

        menu = QMenu(self)
        menu.setObjectName("chatMenu")
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setFixedWidth(CHAT_MENU_WIDTH)
        action = QWidgetAction(menu)
        action.setDefaultWidget(tokens)
        menu.addAction(action)
        menu.addSeparator()

        colors = THEMES[self._theme]
        rename = menu.addAction(icon("pencil", colors["text"], 16), "Premenovať")
        rename.triggered.connect(lambda: QTimer.singleShot(0, row.begin_edit))
        delete = menu.addAction(icon("trash", colors["danger"], 16), "Vymazať")
        delete.triggered.connect(lambda: QTimer.singleShot(0, lambda: self.chat_delete_requested.emit(chat_id)))

        row.set_menu_open(True)
        menu.exec(row.mapToGlobal(QPoint(row.width() - CHAT_MENU_WIDTH, row.height())))
        row.set_menu_open(False)
        menu.deleteLater()
