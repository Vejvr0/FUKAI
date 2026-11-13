# --- ./ui/composer.py ---


from __future__ import annotations
from pathlib import Path
from typing import Callable
from PyQt6.QtWidgets import (
    QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QVBoxLayout, QLabel, QMenu,
    QPlainTextEdit, QToolButton, QWidget, QWidgetAction
)
from PyQt6.QtCore import QEvent, QObject, QPoint, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QKeyEvent, QPalette, QTextOption
from ui.attachment_bar import AttachmentBar
from ui.constants import (
    COMPOSER_BUTTON, COMPOSER_INPUT_MAX_HEIGHT, MODEL_MENU_WIDTH, MODEL_PILL_TEXT_WIDTH, NO_MODEL,
    WEB_BUTTON_OFF, WEB_BUTTON_ON
)
from ui.formatting import model_subtitle
from ui.icons import icon
from ui.style import THEMES, qcolor

__all__ = ["Composer"]


class _Input(QPlainTextEdit):
    submitted = pyqtSignal()
    
    
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("composerInput")
        self.setPlaceholderText("Napíš správu...")
        self.setTabChangesFocus(True)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.document().setDocumentMargin(2)
        self.textChanged.connect(self._fit)
        self._fit()
    
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.insertPlainText("\n")
            else:
                self.submitted.emit()
            return
        super().keyPressEvent(event)
    
    
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit()
    
    
    def _fit(self) -> None:
        lines = max(1, round(self.document().documentLayout().documentSize().height()))
        margins = self.contentsMargins()
        height = (lines * self.fontMetrics().lineSpacing() + 2 * self.document().documentMargin() + margins.top() + margins.bottom())
        height = min(round(height), COMPOSER_INPUT_MAX_HEIGHT)
        if height != self.height():
            self.setFixedHeight(height)
        policy = (Qt.ScrollBarPolicy.ScrollBarAsNeeded if height >= COMPOSER_INPUT_MAX_HEIGHT else Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(policy)


class _ModelRow(QFrame):
    clicked = pyqtSignal()
    delete_clicked = pyqtSignal()
    
    
    def __init__(self, model: dict, selected: bool, check_icon: QIcon, trash_icon: QIcon, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("modelRow")
        self._hand = False
        self.setToolTip(model["path"])
        
        name = QLabel(model["title"])
        name.setObjectName("modelName")
        sub = QLabel(model_subtitle(model))
        sub.setObjectName("modelSub")
        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(1)
        text.addWidget(name)
        text.addWidget(sub)
        
        check = QLabel()
        check.setFixedSize(16, 16)
        if selected:
            check.setPixmap(check_icon.pixmap(QSize(16, 16)))
            
        self._trash = QToolButton()
        self._trash.setObjectName("modelTrash")
        self._trash.setFixedSize(24, 24)
        self._trash.setIcon(trash_icon)
        self._trash.setToolTip("Zmazať model")
        self._trash.clicked.connect(lambda: self.delete_clicked.emit())
        policy = self._trash.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self._trash.setSizePolicy(policy)
        self._trash.hide()
        
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 7, 6, 7)
        row.setSpacing(6)
        row.addLayout(text, 1)
        row.addWidget(self._trash)
        row.addWidget(check)
    
    
    def enterEvent(self, event) -> None:
        self._trash.show()
        self._set_hand(True)
        super().enterEvent(event)
    
    
    def leaveEvent(self, event) -> None:
        self._trash.hide()
        self._set_hand(False)
        super().leaveEvent(event)
    
    
    def hideEvent(self, event) -> None:
        self._set_hand(False)
        super().hideEvent(event)
    
    
    def _set_hand(self, on: bool) -> None:
        if on != self._hand:
            self._hand = on
            if on:
                QApplication.setOverrideCursor(Qt.CursorShape.PointingHandCursor)
            else:
                QApplication.restoreOverrideCursor()
    
    
    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class _ModelPill(QToolButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("modelPill")
        self.setFixedHeight(COMPOSER_BUTTON)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._text = QLabel()
        self._text.setObjectName("pillText")
        self._chev = QLabel()
        self._chev.setFixedSize(16, 16)
        for label in (self._text, self._chev):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 12, 0)
        row.setSpacing(6)
        row.addWidget(self._text)
        row.addWidget(self._chev)
        self._chev_icon: QIcon | None = None
        self._full = NO_MODEL

    
    def sizeHint(self) -> QSize:
        return QSize(self.layout().sizeHint().width(), COMPOSER_BUTTON)
    
    
    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()
    
    
    def set_text(self, text: str) -> None:
        self._full = text
        metrics = self._text.fontMetrics()
        self._text.setText(metrics.elidedText(text, Qt.TextElideMode.ElideRight, MODEL_PILL_TEXT_WIDTH))
        self.setToolTip(text)
        self.updateGeometry()
    
    
    def set_chevron(self, chev_icon: QIcon) -> None:
        self._chev_icon = chev_icon
        self._update_chevron()
    
    
    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.EnabledChange:
            self._update_chevron()
        elif event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self.set_text(self._full)
    
    
    def _update_chevron(self) -> None:
        if self._chev_icon is not None:
            mode = QIcon.Mode.Normal if self.isEnabled() else QIcon.Mode.Disabled
            self._chev.setPixmap(self._chev_icon.pixmap(QSize(16, 16), mode))


class Composer(QFrame):
    send_requested = pyqtSignal(str)
    stop_requested = pyqtSignal()
    model_selected = pyqtSignal(int)
    add_model_requested = pyqtSignal()
    delete_model_requested = pyqtSignal(int)
    attach_requested = pyqtSignal()
    files_dropped = pyqtSignal(object)
    web_toggled = pyqtSignal(bool)
    
    
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("composer")
        self.setProperty("focused", False)
        
        self._busy = False
        self._generating = False
        self._loading = False
        self._model_id: int | None = None
        self._model_source: Callable[[], list[dict]] = list
        self._theme = "light"
        
        self._attachments_enabled = True
        self._sent: list = []
        self.attachments = AttachmentBar()

        self._input = _Input()
        self._input.setAcceptDrops(False)
        self.setAcceptDrops(True)
        self._input.installEventFilter(self)
        self._input.submitted.connect(self._submit)
        self._input.textChanged.connect(self._update_buttons)
        self.attachments.changed.connect(self._update_buttons)
        
        hint = QLabel("Enter odoslať · Shift+Enter nový riadok")
        hint.setObjectName("composerHint")
        
        self._attach = self._round_button("Prílohy")
        self._attach.clicked.connect(self.attach_requested)
        self._web = self._round_button(WEB_BUTTON_OFF)
        self._web.setCheckable(True)
        self._web.toggled.connect(self._refresh_web)
        self._web.toggled.connect(self.web_toggled)
        
        self._pill = _ModelPill()
        self._pill.clicked.connect(self._open_model_menu)
        self._pill.set_text(NO_MODEL)
        
        self._send = QToolButton()
        self._send.setObjectName("send")
        self._send.setFixedSize(COMPOSER_BUTTON, COMPOSER_BUTTON)
        self._send.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send.clicked.connect(self._on_send_clicked)
        
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(8)
        bar.addWidget(hint, 1)
        bar.addWidget(self._attach)
        bar.addWidget(self._web)
        bar.addWidget(self._pill)
        bar.addWidget(self._send)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 12, 10)
        layout.setSpacing(6)
        layout.addWidget(self.attachments)
        layout.addWidget(self._input)
        layout.addLayout(bar)
        
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(30)
        self._shadow.setOffset(0, 10)
        self.setGraphicsEffect(self._shadow)
        
        self.set_theme(self._theme)
    
    
    def _round_button(self, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName("roundButton")
        button.setFixedSize(COMPOSER_BUTTON, COMPOSER_BUTTON)
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button


    def text(self) -> str:
        return self._input.toPlainText().strip()


    def dragEnterEvent(self, event) -> None:
        if self._attachments_enabled and event.mimeData().hasUrls():
            event.acceptProposedAction()


    def dragMoveEvent(self, event) -> None:
        if self._attachments_enabled and event.mimeData().hasUrls():
            event.acceptProposedAction()


    def dropEvent(self, event) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if self._attachments_enabled and paths:
            event.acceptProposedAction()
            self.files_dropped.emit(paths)


    def set_features(self, attachments: bool, web_search: bool) -> None:
        self._attachments_enabled = attachments
        self._attach.setVisible(attachments)
        self._web.setVisible(web_search)
        if not web_search:
            self.set_web(False)


    def set_web(self, on: bool) -> None:
        blocked = self._web.blockSignals(True)
        self._web.setChecked(on)
        self._web.blockSignals(blocked)
        self._refresh_web()


    def _refresh_web(self) -> None:
        on = self._web.isChecked()
        self._web.setIcon(self._icon_web_on if on else self._icon_web)
        self._web.setToolTip(WEB_BUTTON_ON if on else WEB_BUTTON_OFF)
    
    
    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self.attachments.set_theme(theme)
        tokens = THEMES[theme]
        text = tokens["text"]
        self._attach.setIcon(icon("plus", text))
        self._icon_web = icon("globe", text)
        self._icon_web_on = icon("globe", tokens["send_text"], disabled_color=text)
        self._refresh_web()
        self._pill.set_chevron(icon("chev", text, 16))
        self._icon_send = icon("up", tokens["send_text"], disabled_color=text)
        self._icon_stop = icon("stop", tokens["send_text"], disabled_color=text)
        self._check = icon("check", tokens["accent_strong"], 16)
        self._trash = icon("trash", tokens["danger"], 16)
        self._shadow.setColor(qcolor(tokens["shadow"]))
        palette = self._input.palette()
        palette.setColor(QPalette.ColorRole.PlaceholderText, qcolor(tokens["text_muted"]))
        self._input.setPalette(palette)
        self._update_buttons()
        
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._input and event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            self.setProperty("focused", event.type() == QEvent.Type.FocusIn)
            self.style().unpolish(self)
            self.style().polish(self)
        return False
    
    
    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._pill.setEnabled(not busy)
        self._web.setEnabled(not busy)
        self._update_buttons()
    
    
    def set_loading(self, loading: bool) -> None:
        self._loading = loading
        self._update_buttons()
    
    
    def begin_turn(self, question: str) -> None:
        if self._input.toPlainText().strip() == question:
            self._input.clear()
        sent = self.attachments.attachments()
        if sent:
            self._sent = sent
            self.attachments.clear()
        self._generating = True
        self._update_buttons()
    
    
    def end_turn(self) -> None:
        self._sent = []
        self._generating = False
        self._update_buttons()
    
    
    def roll_back(self, question: str) -> None:
        self._generating = False
        if self._sent and not self.attachments.attachments():
            self.attachments.restore(self._sent)
        self._sent = []
        if not self._input.toPlainText().strip():
            self._input.setPlainText(question)
            self._input.moveCursor(self._input.textCursor().MoveOperation.End)
        self._input.setFocus()
        self._update_buttons()
    
    
    def set_model(self, model: dict | None) -> None:
        self._model_id = model["id"] if model else None
        self._pill.set_text(model["title"] if model else NO_MODEL)
    
    
    def set_model_source(self, source: Callable[[], list[dict]]) -> None:
        self._model_source = source
    
    
    def focus_input(self) -> None:
        self._input.setFocus()
    
    
    def _submit(self) -> None:
        text = self._input.toPlainText().strip()
        if self._busy or not (text or self.attachments.attachments()):
            return
        self.send_requested.emit(text)
    
    
    def _on_send_clicked(self) -> None:
        if self._generating:
            self.stop_requested.emit()
        else:
            self._submit()
    
    
    def _update_buttons(self) -> None:
        if self._generating:
            self._send.setIcon(self._icon_stop)
            self._send.setEnabled(not self._loading)
            self._send.setToolTip("Model sa načítava – zastaviť sa dá až odpoveď" if self._loading else "Zastaviť generovanie")
        else:
            self._send.setIcon(self._icon_send)
            self._send.setEnabled(not self._busy and bool(self._input.toPlainText().strip()
                                                          or self.attachments.attachments()))
            self._send.setToolTip("Odpoveď beží v inom chate" if self._busy else "Odoslať")
    
    
    def _open_model_menu(self) -> None:
        menu = QMenu(self)
        menu.setObjectName("modelMenu")
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setFixedWidth(MODEL_MENU_WIDTH)
        menu.setToolTipsVisible(True)

        label = QLabel("MODEL")
        label.setObjectName("menuLabel")
        self._add_widget(menu, label)

        models = self._model_source()
        if not models:
            empty = QLabel("Zatiaľ žiadny model")
            empty.setObjectName("modelEmpty")
            self._add_widget(menu, empty)
        for model in models:
            row = _ModelRow(model, model["id"] == self._model_id, self._check, self._trash)
            row.clicked.connect(lambda model_id=model["id"]: self._choose(menu, model_id))
            row.delete_clicked.connect(lambda model_id=model["id"]: self._delete(menu, model_id))
            self._add_widget(menu, row)

        menu.addSeparator()
        add = menu.addAction(icon("plus", THEMES[self._theme]["text"]), "Pridať .gguf model…")
        add.triggered.connect(lambda: QTimer.singleShot(0, self.add_model_requested.emit))

        size = menu.sizeHint()
        pos = self._pill.mapToGlobal(QPoint(self._pill.width() - size.width(), -size.height() - 8))
        menu.exec(pos)
        menu.deleteLater()
    
    
    @staticmethod
    def _add_widget(menu: QMenu, widget: QWidget) -> None:
        action = QWidgetAction(menu)
        action.setDefaultWidget(widget)
        menu.addAction(action)
    
    
    def _delete(self, menu: QMenu, model_id: int) -> None:
        menu.close()
        QTimer.singleShot(0, lambda: self.delete_model_requested.emit(model_id))
    
    
    def _choose(self, menu: QMenu, model_id: int) -> None:
        menu.close()
        if model_id != self._model_id:
            self.model_selected.emit(model_id)
