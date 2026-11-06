from __future__ import annotations
from math import ceil
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea, QTextBrowser, QWidget
)
from PyQt6.QtCore import QEvent, QObject, QSize, Qt, QTimer
from PyQt6.QtGui import (
    QColor, QFontMetricsF, QIcon, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextOption
)
from ui.constants import (
    AVATAR_SIZE, BUBBLE_MAX_RATIO, CARET, COMPOSER_MAX_WIDTH, ICO, LINE_HEIGHT,
    MESSAGE_SPACING, STICK_MARGIN, STREAM_FLUSH_MS
)
from ui.formatting import answer_meta
from ui.style import THEMES

__all__ = ["MessageList"]


class _TextView(QTextBrowser):
    def __init__(self, object_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        
        self.setOpenLinks(False)
        self.viewport().setAutoFillBackground(False)
        self.document().setDocumentMargin(0)
        self._caret = False
        self._fit: tuple[int, bool] | None = None
        
        
    def set_plain(self, text: str) -> None:
        self.setPlainText(text)
        cursor = QTextCursor(self.document())
        cursor.select(QTextCursor.SelectionType.Document)
        block = QTextBlockFormat()
        block.setLineHeight(LINE_HEIGHT, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        cursor.mergeBlockFormat(block)
        self._caret = False
    
    
    def fit(self, width: int, *, shrink: bool = False) -> None:
        if width <= 0:
            return
        self._fit = (width, shrink)
        doc = self.document()
        if shrink:
            doc.setTextWidth(-1)
            width = min(ceil(doc.idealWidth()) + 1, width)
        doc.setTextWidth(width)
        trailing = round(QFontMetricsF(self.font()).height() * (LINE_HEIGHT - 100) / 100)
        self.setViewportMargins(0, 0, 0, -trailing)
        size = QSize(width, ceil(doc.size().height()) - trailing)
        if size != self.size():
            self.setFixedSize(size)
    
    
    
    def show_caret(self, color: str) -> None:
        if self._caret:
            return
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        self._end().insertText(CARET, fmt)
        self._caret = True
    
    
    
    def insert(self, text: str) -> None:
        cursor = self._end()
        if self._caret:
            cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter)
        cursor.insertText(text, QTextCharFormat())
    
    
    
    def _end(self) -> QTextCursor:
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        return cursor
    
    
    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange) and self._fit:
            width, shrink = self._fit
            self.fit(width, shrink=shrink)
    
    
    def wheelEvent(self, event) -> None:
        event.ignore()


class _UserMessage(QWidget):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.text = _TextView("bubbleText")
        self.text.set_plain(text)
        bubble = QFrame()
        bubble.setObjectName("bubble")
        inner = QVBoxLayout(bubble)
        inner.setContentsMargins(16, 10, 16, 10)
        inner.addWidget(self.text)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(bubble)
        
    
    def fit(self, width: int) -> None:
        self.text.fit(int(width * BUBBLE_MAX_RATIO) - 32, shrink=True)


class _AnswerMessage(QWidget):
    def __init__(self, avatar: QIcon, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        face = QLabel()
        face.setObjectName("avatar")
        face.setFixedSize(AVATAR_SIZE, AVATAR_SIZE)
        face.setPixmap(avatar.pixmap(QSize(AVATAR_SIZE, AVATAR_SIZE)))
        self.text = _TextView("answerText")
        self._meta = QLabel()
        self._meta.setObjectName("answerMeta")
        self._meta.hide()
        
        body = QVBoxLayout()
        body.setContentsMargins(0, 4, 0, 0)
        body.setSpacing(8)
        body.addWidget(self.text)
        body.addWidget(self._meta)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        row.addWidget(face, 0, Qt.AlignmentFlag.AlignTop)
        row.addLayout(body, 1)
        
        self._pending: list[str] = []
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.setInterval(STREAM_FLUSH_MS)
        self._flush_timer.timeout.connect(self._flush)
        self._width = 0
        
    
    def fit(self, width: int) -> None:
        self._width = width
        self.text.fit(width - AVATAR_SIZE - 12)
    
    
    def show_answer(self, data: dict) -> None:
        self._flush_timer.stop()
        self._pending.clear()
        self.text.set_plain(data.get("text", ""))
        meta = answer_meta(data)
        self._meta.setText(meta)
        self._meta.setVisible(bool(meta))
        self.fit(self._width)
    
    
    def start(self, caret_color: str) -> None:
        self.text.set_plain("")
        self.text.show_caret(caret_color)
        self.fit(self._width)
    
    
    def append(self, piece: str) -> None:
        self._pending.append(piece)
        if not self._flush_timer.isActive():
            self._flush_timer.start()
    
    
    def _flush(self) -> None:
        if self._pending:
            self.text.insert("".join(self._pending))
            self._pending.clear()
            self.fit(self._width)


class MessageList(QScrollArea):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("messageList")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setAutoFillBackground(False)
        
        self._column = QWidget()
        self._column.setMaximumWidth(COMPOSER_MAX_WIDTH)
        self._column.installEventFilter(self)
        self._items = QVBoxLayout(self._column)
        self._items.setContentsMargins(0, 24, 0, 8)
        self._items.setSpacing(MESSAGE_SPACING)
        self._items.addStretch(1)
        
        content = QWidget()
        row = QHBoxLayout(content)
        row.setContentsMargins(24, 0, 24, 0)
        row.addStretch(1)
        row.addWidget(self._column, 100)
        
        row.addStretch(1)
        self.setWidget(content)
        content.setAutoFillBackground(False)
        
        self._width = 0
        self._stick = True
        self._turn: tuple[_UserMessage, _AnswerMessage] | None = None
        self._avatar = QIcon(str(ICO))
        self._caret_color = THEMES["light"]["accent_strong"]
        
        bar = self.verticalScrollBar()
        bar.rangeChanged.connect(self._on_range_changed)
        bar.valueChanged.connect(self._on_value_changed)

    
    def set_theme(self, theme: str) -> None:
        self._caret_color = THEMES[theme]["accent_strong"]
    
    
    def is_empty(self) -> bool:
        return self._items.count() == 1
    
    
    def set_messages(self, messages: list[dict]) -> None:
        self._clear()
        for message in messages:
            data = message.get("data") or {}
            if message.get("role") == "assistant":
                answer = _AnswerMessage(self._avatar)
                self._add(answer)
                answer.show_answer(data)
            else:
                self._add(_UserMessage(data.get("text", "")))
        self._stick = True
    
    
    def begin_turn(self, question: str) -> None:
        if self._turn is not None:
            return
        user = _UserMessage(question)
        answer = _AnswerMessage(self._avatar)
        self._add(user)
        self._add(answer)
        answer.start(self._caret_color)
        self._turn = (user, answer)
        self._stick = True
    
    
    def append_token(self, piece: str) -> None:
        if self._turn is not None:
            self._turn[1].append(piece)
    
    
    def finish_turn(self, answer: dict) -> None:
        if self._turn is not None:
            self._turn[1].show_answer(answer)
            self._turn = None
    
    
    def roll_back(self) -> None:
        if self._turn is not None:
            for widget in self._turn:
                self._remove(widget)
            self._turn = None
    
    
    def _add(self, widget: QWidget) -> None:
        self._items.insertWidget(self._items.count() - 1, widget)
        widget.fit(self._width)
    
    
    def _clear(self) -> None:
        self._turn = None
        while self._items.count() > 1:
            self._remove(self._items.itemAt(0).widget())
    
    
    def _remove(self, widget: QWidget) -> None:
        self._items.removeWidget(widget)
        widget.hide()
        widget.deleteLater()
    
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._column and event.type() == QEvent.Type.Resize and self._column.width() != self._width:
            self._width = self._column.width()
            for i in range(self._items.count() - 1):
                self._items.itemAt(i).widget().fit(self._width)
        return False
    
    
    def _on_value_changed(self, value: int) -> None:
        self._stick = value >= self.verticalScrollBar().maximum() - STICK_MARGIN
    
    
    def _on_range_changed(self, minimum: int, maximum: int) -> None:
        if self._stick:
            self.verticalScrollBar().setValue(maximum)
