# --- ./ui/text_preview.py ---


from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget
)
from ui.constants import PREVIEW_HEIGHT, PREVIEW_SHADOW, PREVIEW_TITLE, PREVIEW_WIDTH
from ui.formatting import approx_tokens, int_text, tokens_text
from ui.style import THEMES, qcolor

__all__ = ["TextPreviewDialog"]


class TextPreviewDialog(QDialog):
    def __init__(self, title: str, text: str, theme: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(PREVIEW_TITLE)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        card = QFrame()
        card.setObjectName("infoCard")
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(PREVIEW_SHADOW)
        shadow.setOffset(0, 6)
        shadow.setColor(qcolor(THEMES[theme]["shadow"]))
        card.setGraphicsEffect(shadow)

        name = QLabel(title)
        name.setObjectName("infoTitle")
        name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        close = QPushButton("✕")
        close.setObjectName("infoClose")
        close.setFixedSize(24, 24)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(self.accept)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 12)
        head.setSpacing(8)
        head.addWidget(name, 1)
        head.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)

        body = QPlainTextEdit()
        body.setObjectName("previewText")
        body.setReadOnly(True)
        body.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        body.setPlainText(text)
        body.moveCursor(body.textCursor().MoveOperation.Start)

        foot = QLabel(f"{int_text(len(text))} znakov · {tokens_text(approx_tokens(text))}")
        foot.setObjectName("infoKey")
        foot.setContentsMargins(0, 10, 0, 0)

        column = QVBoxLayout(card)
        column.setContentsMargins(20, 16, 20, 18)
        column.setSpacing(0)
        column.addLayout(head)
        column.addWidget(body, 1)
        column.addWidget(foot)

        margin = PREVIEW_SHADOW // 2
        layout = QVBoxLayout(self)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.addWidget(card)
        self.resize(PREVIEW_WIDTH + 2 * margin, PREVIEW_HEIGHT + 2 * margin)


    def showEvent(self, event) -> None:
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is not None:
            center = parent.frameGeometry().center()
            self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)
