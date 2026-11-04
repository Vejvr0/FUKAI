from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from core.hardware import HardwareProfile
from ui.composer import Composer
from ui.constants import COMPOSER_MAX_WIDTH, COMPOSER_SHADOW_ROOM, HEADER_HEIGHT, NEW_CHAT_TITLE

__all__ = ["ChatView"]


def hardware_label(hw: HardwareProfile) -> str:
    ram_gb = f"{hw.ram_total_mb / 1024:.0f} GB RAM"
    if hw.gpu is None:
        return f"CPU · {ram_gb}"
    if hw.gpu.backend == "metal":
        return f"GPU · Apple Metal · {ram_gb}"
    name = hw.gpu.name.removeprefix("NVIDIA ").removeprefix("GeForce ")
    vram = f" · {hw.gpu.vram_total_mb / 1024:.0f} GB VRAM" if hw.gpu.vram_total_mb else ""
    return f"GPU · {name}{vram}"


class ChatView(QWidget):
    def __init__(self, hardware: HardwareProfile, parent=None) -> None:
        super().__init__(parent)
        self._title = QLabel(NEW_CHAT_TITLE)
        self._title.setObjectName("headTitle")
        self._title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        
        header = QFrame()
        header.setObjectName("chatHeader")
        header.setFixedHeight(HEADER_HEIGHT)
        row = QHBoxLayout(header)
        row.setContentsMargins(20, 0, 20, 0)
        row.setSpacing(12)
        row.addWidget(self._title, 1)
        row.addWidget(self._hw_chip(hardware))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header)
        layout.addStretch(1)                    # zoznam správ – ďalší kúsok
        layout.addWidget(self._composer_column())
    
    
    def _composer_column(self) -> QWidget:
        self.composer = Composer()
        foot = QLabel("FUKAI môže robiť chyby. Dôležité informácie si over.")
        foot.setObjectName("composerFoot")
        foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        column = QWidget()
        column.setObjectName("composerColumn")
        # Tieň composera sa kreslí len v hraniciach rodiča – bez okraja by bol po bokoch odseknutý.
        column.setMaximumWidth(COMPOSER_MAX_WIDTH + 2 * COMPOSER_SHADOW_ROOM)
        inner = QVBoxLayout(column)
        inner.setContentsMargins(COMPOSER_SHADOW_ROOM, 0, COMPOSER_SHADOW_ROOM, 0)
        inner.setSpacing(8)
        inner.addWidget(self.composer)
        inner.addWidget(foot)
        
        wrap = QWidget()
        row = QHBoxLayout(wrap)
        row.setContentsMargins(24 - COMPOSER_SHADOW_ROOM, 8, 24 - COMPOSER_SHADOW_ROOM, 14)
        row.addStretch(1)
        row.addWidget(column, 100)              # stretch 100 vs 1: stĺpec berie miesto až po max. šírku,
        row.addStretch(1)                       # zvyšok sa rozdelí rovnako po bokoch → vycentrované
        return wrap
    
    
    @staticmethod
    def _hw_chip(hardware: HardwareProfile) -> QFrame:
        dot = QLabel()
        dot.setObjectName("hwDot")
        dot.setProperty("backend", hardware.backend)
        dot.setFixedSize(8, 8)
        text = QLabel(hardware_label(hardware))
        text.setObjectName("hwText")
        
        chip = QFrame()
        chip.setObjectName("hwChip")
        chip.setFixedHeight(28)
        chip.setToolTip("Detegovaný hardvér")
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