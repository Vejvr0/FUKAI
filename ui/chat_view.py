from __future__ import annotations
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from core.hardware import HardwareProfile
from ui.constants import HEADER_HEIGHT

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
        self._title = QLabel("Nový chat")
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
        layout.addStretch(1)
    
    
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