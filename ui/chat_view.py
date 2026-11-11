from __future__ import annotations
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QSizePolicy, QSpacerItem, QVBoxLayout, QWidget
)
from core.hardware import HardwareProfile
from core.monitor import UsageMonitor
from ui.constants import (
    COMPOSER_MAX_WIDTH, COMPOSER_SHADOW_ROOM, EMPTY_LIFT, HEADER_HEIGHT, ICO, NEW_CHAT_TITLE,
    WELCOME_LOGO, WELCOME_TEXT
)
from ui.composer import Composer
from ui.message_list import MessageList
from ui.usage_panel import UsagePanel
from ui.style import THEMES, qcolor

__all__ = ["ChatView"]


def hardware_label(hw: HardwareProfile) -> str:
    ram_gb = f"{hw.ram_total_mb / 1024:.0f} GB RAM"
    if hw.backend == "cpu":
        return f"CPU · {ram_gb}"
    if hw.gpu.backend == "metal":
        return f"GPU · Apple Metal · {ram_gb}"
    name = hw.gpu.name.removeprefix("NVIDIA ").removeprefix("GeForce ")
    vram = f" · {hw.gpu.vram_total_mb / 1024:.0f} GB VRAM" if hw.gpu.vram_total_mb else ""
    return f"GPU · {name}{vram}"


class _HwChip(QFrame):
    clicked = pyqtSignal()


    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class ChatView(QWidget):
    def __init__(self, hardware: HardwareProfile, monitor: UsageMonitor, parent=None) -> None:
        super().__init__(parent)
        self._title = QLabel(NEW_CHAT_TITLE)
        self._title.setObjectName("headTitle")
        self._title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        self.usage = UsagePanel(monitor)
        chip = self._hw_chip(hardware)
        chip.clicked.connect(self.usage.toggle)

        header = QFrame()
        header.setObjectName("chatHeader")
        header.setFixedHeight(HEADER_HEIGHT)
        row = QHBoxLayout(header)
        row.setContentsMargins(20, 0, 20, 0)
        row.setSpacing(12)
        row.addWidget(self._title, 1)
        row.addWidget(self.usage)
        row.addWidget(chip)

        self.messages = MessageList()
        self._welcome = self._welcome_block()
        self._top = QSpacerItem(0, 0)
        self._bottom = QSpacerItem(0, 0)
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addWidget(header)
        self._layout.addItem(self._top)
        self._layout.addWidget(self._welcome)
        self._layout.addWidget(self.messages, 1)
        self._layout.addWidget(self._composer_column())
        self._layout.addItem(self._bottom)
        self._empty: bool | None = None
        self._set_empty(True)

    
    def _composer_column(self) -> QWidget:
        self.composer = Composer()
        self._foot = QLabel("FUKAI môže robiť chyby. Dôležité informácie si over.")
        self._foot.setObjectName("composerFoot")
        self._foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        policy = self._foot.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self._foot.setSizePolicy(policy)
        
        column = QWidget()
        column.setObjectName("composerColumn")
        column.setMaximumWidth(COMPOSER_MAX_WIDTH + 2 * COMPOSER_SHADOW_ROOM)
        inner = QVBoxLayout(column)
        inner.setContentsMargins(COMPOSER_SHADOW_ROOM, 0, COMPOSER_SHADOW_ROOM, 0)
        inner.setSpacing(8)
        inner.addWidget(self.composer)
        inner.addWidget(self._foot)
        
        wrap = QWidget()
        row = QHBoxLayout(wrap)
        row.setContentsMargins(24 - COMPOSER_SHADOW_ROOM, 8, 24 - COMPOSER_SHADOW_ROOM, 14)
        row.addStretch(1)
        row.addWidget(column, 100)
        row.addStretch(1)
        return wrap
    
    
    def _welcome_block(self) -> QWidget:
        logo = QLabel()
        logo.setFixedSize(WELCOME_LOGO, WELCOME_LOGO)
        logo.setPixmap(QIcon(str(ICO)).pixmap(QSize(WELCOME_LOGO, WELCOME_LOGO)))
        self._logo_shadow = QGraphicsDropShadowEffect(logo)
        self._logo_shadow.setBlurRadius(30)
        self._logo_shadow.setOffset(0, 10)
        logo.setGraphicsEffect(self._logo_shadow)
        text = QLabel(WELCOME_TEXT)
        text.setObjectName("welcomeText")
        
        block = QWidget()
        column = QVBoxLayout(block)
        column.setContentsMargins(0, 0, 0, 20)
        column.setSpacing(16)
        column.addWidget(logo, 0, Qt.AlignmentFlag.AlignHCenter)
        column.addWidget(text, 0, Qt.AlignmentFlag.AlignHCenter)
        return block

    
    def _set_empty(self, empty: bool) -> None:
        if empty == self._empty:
            return
        self._empty = empty
        grow = QSizePolicy.Policy.Expanding if empty else QSizePolicy.Policy.Fixed
        self._top.changeSize(0, 0, QSizePolicy.Policy.Minimum, grow)
        self._bottom.changeSize(0, EMPTY_LIFT if empty else 0, QSizePolicy.Policy.Minimum, grow)
        self._welcome.setVisible(empty)
        self.messages.setVisible(not empty)
        self._foot.setVisible(not empty)
        self._layout.invalidate()
    
    
    def show_messages(self, messages: list[dict]) -> None:
        self.messages.set_messages(messages)
        self._set_empty(not messages)
    
    
    def begin_turn(self, question: str, attachments: list[dict] | None = None, web: bool = False) -> None:
        self._set_empty(False)
        self.messages.begin_turn(question, attachments, web)


    def set_status(self, text: str) -> None:
        self.messages.set_status(text)
    
    
    def append_token(self, piece: str) -> None:
        self.messages.append_token(piece)
    
    
    def finish_turn(self, answer: dict, attachments: list[dict] | None = None) -> None:
        self.messages.finish_turn(answer, attachments)
    
    
    def roll_back(self) -> None:
        self.messages.roll_back()
        self._set_empty(self.messages.is_empty())
    
    
    @staticmethod
    def _hw_chip(hardware: HardwareProfile) -> _HwChip:
        dot = QLabel()
        dot.setObjectName("hwDot")
        dot.setProperty("backend", hardware.backend)
        dot.setFixedSize(8, 8)
        text = QLabel(hardware_label(hardware))
        text.setObjectName("hwText")

        chip = _HwChip()
        chip.setObjectName("hwChip")
        chip.setFixedHeight(28)
        tip = "Detegovaný hardvér\nKliknutím zapneš a vypneš monitor vyťaženia."
        if hardware.gpu is not None and not hardware.gpu_offload:
            tip += f"\n{hardware.gpu.name} sa nepoužíva - engine je len pre CPU."
        chip.setToolTip(tip)
        row = QHBoxLayout(chip)
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(8)
        row.addWidget(dot)
        row.addWidget(text)
        return chip
    
    
    def set_title(self, title: str) -> None:
        self._title.setText(title)
    
    
    def set_theme(self, theme: str) -> None:
        self.composer.set_theme(theme)
        self.messages.set_theme(theme)
        self._logo_shadow.setColor(qcolor(THEMES[theme]["shadow"]))
        