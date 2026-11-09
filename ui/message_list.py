from __future__ import annotations
from html import escape
from math import ceil
from urllib.parse import urlparse
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea, QTextBrowser, QToolButton, QWidget
)
from PyQt6.QtCore import QEvent, QObject, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFontMetricsF, QGuiApplication, QIcon, QTextBlockFormat, QTextCharFormat,
    QTextCursor, QTextOption
)
from ui.attachment_bar import ChipName
from ui.constants import (
    MSG_CHIP_HEIGHT, MSG_CHIP_SPACING,
    AVATAR_SIZE, BOX_MARGIN, BUBBLE_MAX_RATIO, CARET, CODE_HEAD_HEIGHT, CODE_MAX_HEIGHT,
    CODE_NO_LANGUAGE, COMPOSER_MAX_WIDTH, COPY_DONE_LABEL, COPY_LABEL, COPY_RESET_MS, ICO,
    LINE_HEIGHT, MESSAGE_SPACING, STICK_MARGIN, STREAM_FLUSH_MS, WEB_CHIP_LABEL, WEB_CHIP_TOOLTIP,
    WEB_SOURCES_LABEL
)
from ui.formatting import answer_meta
from ui.markdown import MD_FEATURES, PartKind, code_html, split_markdown, style_tables
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
        self._line_height()
        self._caret = False
    
    
    def set_markdown(self, text: str) -> None:
        """Markdown až po dobehnutí odpovede – počas streamovania ide `set_plain`."""
        self.document().setMarkdown(text, MD_FEATURES)
        self._line_height()
        self._caret = False
    
    
    def _line_height(self) -> None:
        cursor = QTextCursor(self.document())
        cursor.select(QTextCursor.SelectionType.Document)
        block = QTextBlockFormat()
        block.setLineHeight(LINE_HEIGHT, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        cursor.mergeBlockFormat(block)
    
    
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


class _Body(QTextBrowser):
    """Okno pre kód a tabuľku: bez zalamovania, s vodorovným posuvníkom a stropom výšky.

    Koliesko si necháva, len kým je kam posúvať – inak ho pustí zoznamu správ.
    """
    
    def __init__(self, object_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setOpenLinks(False)
        self.viewport().setAutoFillBackground(False)        # pozadie kreslí rámec bloku
        self.document().setDocumentMargin(BOX_MARGIN)
    
    
    def fit(self, width: int, cap: int = CODE_MAX_HEIGHT) -> None:
        self.setFixedWidth(width)
        doc = self.document()
        doc.setTextWidth(-1)                                # prirodzená šírka, nie šírka okna
        height = ceil(doc.size().height()) + 2 * self.frameWidth()
        if doc.idealWidth() > width:
            height += self.horizontalScrollBar().sizeHint().height()
        capped = height > cap
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded if capped
                                        else Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(min(height, cap))
    
    
    def reset_view(self) -> None:
        """Po setHtml/setMarkdown zostane kurzor na konci a pohľad za ním odskočí –
        pri širokej tabuľke potom vidno posledné stĺpce. Rozsah posuvníka v tej chvíli
        ešte neexistuje, takže setValue(0) nestačí; treba presunúť kurzor."""
        self.moveCursor(QTextCursor.MoveOperation.Start)
    
    
    def wheelEvent(self, event) -> None:
        bar = self.verticalScrollBar()
        delta = event.angleDelta().y()
        scrollable = bar.maximum() > 0 and (
            (delta < 0 and bar.value() < bar.maximum()) or (delta > 0 and bar.value() > 0))
        if scrollable:
            super().wheelEvent(event)
        else:
            event.ignore()


class _CodeBlock(QFrame):
    def __init__(self, code: str, language: str, theme: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("codeBlock")
        self._code = code
        self._language = language
        
        name = QLabel(language or CODE_NO_LANGUAGE)
        name.setObjectName("codeLang")
        self._copy = QToolButton()
        self._copy.setObjectName("codeCopy")
        self._copy.setText(COPY_LABEL)
        self._copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy.clicked.connect(self._on_copy)
        self._reset = QTimer(self)                          # dieťa widgetu, zanikne s ním
        self._reset.setSingleShot(True)
        self._reset.setInterval(COPY_RESET_MS)
        self._reset.timeout.connect(lambda: self._copy.setText(COPY_LABEL))
        
        head = QFrame()
        head.setObjectName("codeHead")
        head.setFixedHeight(CODE_HEAD_HEIGHT)
        row = QHBoxLayout(head)
        row.setContentsMargins(12, 0, 8, 0)
        row.addWidget(name, 1)
        row.addWidget(self._copy)
        
        self.body = _Body("codeBody")
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(head)
        column.addWidget(self.body)
        self.set_theme(theme)
    
    
    def set_theme(self, theme: str) -> None:
        self.body.setHtml(code_html(self._code, self._language, theme))
        self.body.reset_view()
    
    
    def fit(self, width: int) -> None:
        self.body.fit(width, CODE_MAX_HEIGHT)
        self.setFixedHeight(self.body.height() + CODE_HEAD_HEIGHT)
    
    
    def _on_copy(self) -> None:
        QGuiApplication.clipboard().setText(self._code)
        self._copy.setText(COPY_DONE_LABEL)
        self._reset.start()


class _TableBox(_Body):
    def __init__(self, markdown: str, theme: str, parent: QWidget | None = None) -> None:
        super().__init__("tableBody", parent)
        self._markdown = markdown
        self.set_theme(theme)
    
    
    def set_theme(self, theme: str) -> None:
        doc = self.document()
        doc.setMarkdown(self._markdown, MD_FEATURES)
        style_tables(doc, theme)
        self.reset_view()


class _MessageChip(QFrame):
    """Príloha pri odoslanej správe. Na rozdiel od čipu v composeri sa nedá odobrať -
    správa je odoslaná. Klikateľný je len vtedy, keď má príloha v databáze svoje id,
    teda nie počas rozpísaného ťahu."""

    clicked = pyqtSignal(int)


    def __init__(self, title: str, attachment_id: int | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("msgChip")
        self.setFixedHeight(MSG_CHIP_HEIGHT)
        self._id = attachment_id
        self.setProperty("clickable", attachment_id is not None)
        if attachment_id is None:
            self.setToolTip(title)
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip(f"{title}\nkliknutím zobrazíš text")

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 0, 10, 0)
        row.setSpacing(6)
        row.addWidget(ChipName(title))


    def mouseReleaseEvent(self, event) -> None:
        if self._id is not None and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._id)
        super().mouseReleaseEvent(event)


def _web_chip() -> QFrame:
    """„Web“ nad otázkou - pri nej bolo zapnuté hľadanie (13d). Neklikateľný, zdroje sú pod odpoveďou."""
    chip = QFrame()
    chip.setObjectName("msgChip")
    chip.setProperty("web", True)
    chip.setFixedHeight(MSG_CHIP_HEIGHT)
    chip.setToolTip(WEB_CHIP_TOOLTIP)
    label = QLabel(WEB_CHIP_LABEL)
    label.setObjectName("webChipText")
    row = QHBoxLayout(chip)
    row.setContentsMargins(10, 0, 10, 0)
    row.addWidget(label)
    return chip


class _UserMessage(QWidget):
    """Bublina s otázkou a nad ňou čipy príloh (a „Web“). Správa bez textu (iba príloha)
    bublinu nedostane vôbec - prázdna bublina vyzerá ako chyba."""

    preview_requested = pyqtSignal(int)


    def __init__(self, text: str, attachments: list[dict] | None = None, web: bool = False,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.text: _TextView | None = None

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(MSG_CHIP_SPACING)

        if attachments or web:
            chips = QHBoxLayout()
            chips.setContentsMargins(0, 0, 0, 0)
            chips.setSpacing(MSG_CHIP_SPACING)
            chips.addStretch(1)
            if web:
                chips.addWidget(_web_chip())
            for item in attachments or ():
                chip = _MessageChip(item["title"], item.get("id"))
                chip.clicked.connect(self.preview_requested)
                chips.addWidget(chip)
            column.addLayout(chips)

        if text:
            self.text = _TextView("bubbleText")
            self.text.set_plain(text)
            bubble = QFrame()
            bubble.setObjectName("bubble")
            inner = QVBoxLayout(bubble)
            inner.setContentsMargins(16, 10, 16, 10)
            inner.addWidget(self.text)
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addStretch(1)
            row.addWidget(bubble)
            column.addLayout(row)


    def fit(self, width: int) -> None:
        if self.text is not None:
            self.text.fit(int(width * BUBBLE_MAX_RATIO) - 32, shrink=True)


class _AnswerMessage(QWidget):
    """Počas streamovania jeden `_TextView` s obyčajným textom, po dobehnutí zoznam
    častí: markdown, bloky kódu a tabuľky (§8 krok 9, kúsok 6b)."""

    def __init__(self, avatar: QIcon, theme: str = "light", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        face = QLabel()
        face.setObjectName("avatar")
        face.setFixedSize(AVATAR_SIZE, AVATAR_SIZE)
        face.setPixmap(avatar.pixmap(QSize(AVATAR_SIZE, AVATAR_SIZE)))
        self.text: _TextView | None = None          # vzniká až pri streamovaní
        self._meta = QLabel()
        self._meta.setObjectName("answerMeta")
        self._meta.hide()
        self._status = QLabel()                     # „Hľadám na webe…“ pred prvým tokenom
        self._status.setObjectName("answerStatus")
        self._status.hide()
        self._sources = QLabel()                    # zdroje z webu pod odpoveďou
        self._sources.setObjectName("answerSources")
        self._sources.setTextFormat(Qt.TextFormat.RichText)
        self._sources.setWordWrap(True)
        self._sources.setOpenExternalLinks(True)    # QDesktopServices.openUrl - prehliadač
        self._sources.linkHovered.connect(self._sources.setToolTip)
        self._sources.hide()
        self._source_rows: list[dict] = []

        self._body = QVBoxLayout()
        self._body.setContentsMargins(0, 4, 0, 0)
        self._body.setSpacing(8)
        self._body.addWidget(self._status)
        self._body.addWidget(self._sources)
        self._body.addWidget(self._meta)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        row.addWidget(face, 0, Qt.AlignmentFlag.AlignTop)
        row.addLayout(self._body, 1)

        self._parts: list[QWidget] = []
        self._theme = theme
        self._pending: list[str] = []
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.setInterval(STREAM_FLUSH_MS)
        self._flush_timer.timeout.connect(self._flush)
        self._width = 0


    def fit(self, width: int) -> None:
        self._width = width
        inner = width - AVATAR_SIZE - 12
        if self.text is not None:
            self.text.fit(inner)
        for part in self._parts:
            part.fit(inner)


    def show_answer(self, data: dict) -> None:
        self._flush_timer.stop()
        self._pending.clear()
        self.set_status("")
        self._build(data.get("text", ""))
        self._source_rows = list((data.get("web") or {}).get("sources") or [])
        self._render_sources()
        meta = answer_meta(data)
        self._meta.setText(meta)
        self._meta.setVisible(bool(meta))
        self.fit(self._width)


    def set_theme(self, theme: str) -> None:
        """Kód a tabuľky treba prerenderovať – farby sú zapečené v HTML a vo formáte."""
        self._theme = theme
        for part in self._parts:
            if isinstance(part, (_CodeBlock, _TableBox)):
                part.set_theme(theme)
        self._render_sources()                      # farba odkazov je v HTML
        self.fit(self._width)


    def set_status(self, text: str) -> None:
        self._status.setText(text)
        self._status.setVisible(bool(text))


    def _render_sources(self) -> None:
        """Názvy a adresy sú z cudzích stránok - do HTML idú len escapované a odkazom
        sa stane iba http(s) adresa."""
        rows = []
        link = THEMES[self._theme]["accent_strong"]
        for source in self._source_rows:
            url = str(source.get("url") or "")
            title = escape(str(source.get("title") or url))
            label = f"[{source.get('n', len(rows) + 1)}] {title}"
            domain = urlparse(url).netloc.removeprefix("www.")
            if urlparse(url).scheme in ("http", "https"):
                label = f'<a href="{escape(url, quote=True)}" style="color: {link}; text-decoration: none;">{label}</a>'
            rows.append(f"{label} · {escape(domain)}" if domain else label)
        if rows:
            self._sources.setText(f"<b>{WEB_SOURCES_LABEL}</b><br>" + "<br>".join(rows))
        self._sources.setVisible(bool(rows))


    def start(self, caret_color: str) -> None:
        self._clear()
        self.text = _TextView("answerText")
        self._body.insertWidget(self._body.indexOf(self._status) + 1, self.text)
        self.text.set_plain("")
        self.text.show_caret(caret_color)
        self.fit(self._width)


    def append(self, piece: str) -> None:
        if self._status.isVisible():
            self.set_status("")
        self._pending.append(piece)
        if not self._flush_timer.isActive():
            self._flush_timer.start()


    def _flush(self) -> None:
        if self._pending and self.text is not None:
            self.text.insert("".join(self._pending))
            self._pending.clear()
            self.fit(self._width)


    def _build(self, text: str) -> None:
        self._clear()
        for index, part in enumerate(split_markdown(text)):
            if part.kind is PartKind.CODE:
                widget = _CodeBlock(part.content, part.language, self._theme)
            elif part.kind is PartKind.TABLE:
                widget = _TableBox(part.content, self._theme)
            else:
                widget = _TextView("answerText")
                widget.set_markdown(part.content)
            self._parts.append(widget)
            self._body.insertWidget(index, widget)


    def _clear(self) -> None:
        for widget in (*self._parts, self.text):
            if widget is None:
                continue
            self._body.removeWidget(widget)
            widget.hide()                           # bez toho zostane visieť na starom mieste
            widget.deleteLater()
        self._parts.clear()
        self.text = None


class MessageList(QScrollArea):
    preview_requested = pyqtSignal(int)

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
        self._theme = "light"
        self._caret_color = THEMES["light"]["accent_strong"]
        
        bar = self.verticalScrollBar()
        bar.rangeChanged.connect(self._on_range_changed)
        bar.valueChanged.connect(self._on_value_changed)

    
    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self._caret_color = THEMES[theme]["accent_strong"]
        for index in range(self._items.count() - 1):
            widget = self._items.itemAt(index).widget()
            if isinstance(widget, _AnswerMessage):
                widget.set_theme(theme)
    
    
    def is_empty(self) -> bool:
        return self._items.count() == 1
    
    
    def set_messages(self, messages: list[dict]) -> None:
        self._clear()
        for message in messages:
            data = message.get("data") or {}
            if message.get("role") == "assistant":
                answer = _AnswerMessage(self._avatar, self._theme)
                self._add(answer)
                answer.show_answer(data)
            else:
                user = _UserMessage(data.get("text", ""), message.get("attachments"), bool(data.get("web")))
                user.preview_requested.connect(self.preview_requested)
                self._add(user)
        self._stick = True
    
    
    def begin_turn(self, question: str, attachments: list[dict] | None = None, web: bool = False) -> None:
        if self._turn is not None:
            return
        user = _UserMessage(question, attachments, web)
        answer = _AnswerMessage(self._avatar, self._theme)
        self._add(user)
        self._add(answer)
        answer.start(self._caret_color)
        self._turn = (user, answer)
        self._stick = True
    
    
    def append_token(self, piece: str) -> None:
        if self._turn is not None:
            self._turn[1].append(piece)


    def set_status(self, text: str) -> None:
        if self._turn is not None:
            self._turn[1].set_status(text)
    
    
    def finish_turn(self, answer: dict) -> None:
        if self._turn is None:
            return
        bar = self.verticalScrollBar()
        value = bar.value()
        self._turn[1].show_answer(answer)       # obsah sa prestaví na časti, výška sa zmení
        self._turn = None
        if not self._stick:                     # kto čítal vyššie, nemá odskočiť dole
            QTimer.singleShot(0, lambda: bar.setValue(min(value, bar.maximum())))
    
    
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
        maximum = self.verticalScrollBar().maximum()
        if maximum <= 0:
            return          # obsah sa zmestí do okna – pri prestavbe správy sa rozsah
                            # nakrátko zmenší na nulu a "som dole" sa nesmie prepnúť
        self._stick = value >= maximum - STICK_MARGIN
    
    
    def _on_range_changed(self, minimum: int, maximum: int) -> None:
        if self._stick:
            self.verticalScrollBar().setValue(maximum)
