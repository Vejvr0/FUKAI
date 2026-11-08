from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QWidget
)
from core.settings import ModelMeta
from ui.constants import (
    DASH, KV_SAMPLE, MODEL_INFO_KEY_WIDTH, MODEL_INFO_SHADOW, MODEL_INFO_TITLE, MODEL_INFO_WIDTH
)
from ui.formatting import int_text, size_text
from ui.style import THEMES, qcolor

__all__ = [
    "ModelInfoDialog",
    "info_rows"
]


def info_rows(model: dict, meta: ModelMeta) -> list[tuple[str, str]]:
    kv_mb = meta.kv_cache_mb(KV_SAMPLE)
    size_mb = model.get("size_mb")
    return [
        ("Názov v metadátach", meta.name or DASH),
        ("Architektúra", meta.arch or DASH),
        ("Parametre", meta.size_label or DASH),
        ("Kvantizácia", meta.quant or DASH),
        ("Kontext modelu", f"{int_text(meta.n_ctx_train)} tokenov" if meta.n_ctx_train else DASH),
        ("Vrstvy", f"{meta.n_layers} + výstupná" if meta.n_layers else DASH),
        (f"KV cache / {int_text(KV_SAMPLE)} tokenov", size_text(kv_mb) if kv_mb is not None else DASH),
        ("Chat template", "áno" if meta.has_chat_template else "nie"),
        ("Veľkosť súboru", size_text(size_mb) if size_mb else DASH),
        ("Súbor", model["path"])
    ]


class ModelInfoDialog(QDialog):
    def __init__(self, model: dict, meta: ModelMeta, theme: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(MODEL_INFO_TITLE)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        card = QFrame()
        card.setObjectName("infoCard")
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(MODEL_INFO_SHADOW)
        shadow.setOffset(0, 6)
        shadow.setColor(qcolor(THEMES[theme]["shadow"]))
        card.setGraphicsEffect(shadow)

        title = QLabel(model["title"])
        title.setObjectName("infoTitle")
        title.setWordWrap(True)

        close = QPushButton("✕")
        close.setObjectName("infoClose")
        close.setFixedSize(24, 24)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(self.accept)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 14)
        head.setSpacing(8)
        head.addWidget(title, 1)
        head.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(7)
        for row, (name, value) in enumerate(info_rows(model, meta)):
            key = QLabel(name)
            key.setObjectName("infoKey")
            key.setFixedWidth(MODEL_INFO_KEY_WIDTH)
            text = QLabel(value)
            text.setObjectName("infoValue")
            text.setWordWrap(True)
            text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(key, row, 0, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(text, row, 1)
        grid.setColumnStretch(1, 1)

        column = QVBoxLayout(card)
        column.setContentsMargins(20, 16, 20, 18)
        column.setSpacing(0)
        column.addLayout(head)
        column.addLayout(grid)

        margin = MODEL_INFO_SHADOW // 2
        layout = QVBoxLayout(self)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.addWidget(card)
        self.setFixedWidth(MODEL_INFO_WIDTH + 2 * margin)


    def showEvent(self, event) -> None:
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is not None:
            center = parent.frameGeometry().center()
            self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)
