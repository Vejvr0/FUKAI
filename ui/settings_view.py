from __future__ import annotations
from PyQt6.QtCore import Qt, QSize, QTimer, QEvent, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QWidget, QScrollArea, QSizePolicy,
    QLineEdit, QPushButton
)
from ui.constants import (
    HEADER_HEIGHT, SETTINGS_FOOT, PAGE_MAX_WIDTH, SETTINGS_SAVED_FLASH, SETTINGS_SAVED_MS,
    SETTINGS_SAVED_TEXT, SETTINGS_TITLE, SET_ICON_BOX, SET_ICON_SIZE, FOUND_ITEM_HEIGHT, ICON_GAP,
    OPEN_FOLDER_LABEL, PATH_ROW_HEIGHT
)
from ui.icons import icon
from ui.formatting import model_subtitle
from ui.toggle_switch import ToggleSwitch
from ui.style import THEMES

__all__ = ["SettingsView"]


class _FoundRow(QFrame):
    clicked = pyqtSignal(object)


    def __init__(self, model: dict, cube: QIcon, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("foundItem")
        self.setFixedHeight(FOUND_ITEM_HEIGHT)
        self._model = model
        self.setToolTip(self._model["path"])
        self._title = self._model["title"]

        badge = QLabel()
        badge.setFixedSize(16, 16)
        badge.setPixmap(cube.pixmap(QSize(16, 16)))

        self._name = QLabel()
        self._name.setObjectName("fName")
        self._name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._name.setCursor(Qt.CursorShape.PointingHandCursor)
        self._name.installEventFilter(self)

        meta = QLabel(model_subtitle(self._model))
        meta.setObjectName("fMeta")

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 0, 10, 0)
        row.setSpacing(10)
        row.addWidget(badge)
        row.addWidget(self._name, 1)
        row.addWidget(meta)
        self._apply_title()


    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_title()


    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._apply_title()


    def eventFilter(self, obj, event):
        if obj == self._name and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self._on_model_clicked()
                return True
        return super().eventFilter(obj, event)


    def _on_model_clicked(self) -> None:
        self.clicked.emit(self._model)


    def _apply_title(self) -> None:
        metrics = self._name.fontMetrics()
        self._name.setText(metrics.elidedText(self._title, Qt.TextElideMode.ElideRight, max(0, self._name.width())))


class SettingsView(QWidget):
    theme_changed = pyqtSignal(str)
    attachments_changed = pyqtSignal(bool)
    websearch_changed = pyqtSignal(bool)
    open_folder_requested = pyqtSignal()
    opened = pyqtSignal()
    model_info_requested = pyqtSignal(object)


    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = "light"
        self._icons: list[tuple[QLabel, str]] = []
        self._models: list[dict] = []

        self._title = QLabel(SETTINGS_TITLE)
        self._title.setObjectName("headTitle")
        self._title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        self._saved = QLabel(SETTINGS_SAVED_TEXT)
        self._saved.setObjectName("savedNote")
        self._saved.setProperty("flash", False)
        self._saved_timer = QTimer(self)
        self._saved_timer.setSingleShot(True)
        self._saved_timer.timeout.connect(self._clear_flash)

        header = QFrame()
        header.setObjectName("settingsHeader")
        header.setFixedHeight(HEADER_HEIGHT)
        row = QHBoxLayout(header)
        row.setContentsMargins(20, 0, 20, 0)
        row.setSpacing(12)
        row.addWidget(self._title, 1)
        row.addWidget(self._saved)

        self._theme_switch = ToggleSwitch()
        self._web_switch = ToggleSwitch()
        self._attach_switch = ToggleSwitch()
        self._theme_switch.toggled.connect(self._on_theme_toggled)
        self._web_switch.toggled.connect(self._on_web_toggled)
        self._attach_switch.toggled.connect(self._on_attach_toggled)

        wrap = QWidget()
        wrap.setObjectName("settingsWrap")
        wrap.setMaximumWidth(PAGE_MAX_WIDTH)
        self._wrap = QVBoxLayout(wrap)
        self._wrap.setContentsMargins(0, 0, 0, 0)
        self._wrap.setSpacing(0)

        self._wrap.addWidget(self._group("Vzhľad"))
        self._wrap.addWidget(self._card([self._set_row("moon", "Tmavý vzhľad", "Prepne farby celej aplikácie. Vypnuté = svetlý vzhľad.", self._theme_switch)]))
        self._wrap.addWidget(self._group("Funkcie chatu"))
        self._wrap.addWidget(self._card([
            self._set_row("globe", "Vyhľadávanie na webe", "Zobrazí v chate tlačidlo pre web. Keď je vypnuté, FUKAI nikdy nepristupuje na internet.", self._web_switch),
            self._set_row("clip", "Prílohy v chate", "Povolí vkladanie súborov do správy: txt, md, pdf, xlsx, docx, csv…", self._attach_switch),
        ]))
        self._wrap.addWidget(self._group("Modely"))
        self._wrap.addWidget(self._models_card())

        foot = QLabel(SETTINGS_FOOT)
        foot.setObjectName("pageFoot")
        foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wrap.addSpacing(18)
        self._wrap.addWidget(foot)
        self._wrap.addStretch(1)

        body = QScrollArea()
        body.setObjectName("settingsBody")
        body.setWidgetResizable(True)
        body.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        holder = QWidget()
        holder_row = QHBoxLayout(holder)
        holder_row.setContentsMargins(24, 8, 24, 24)
        holder_row.addStretch(1)
        holder_row.addWidget(wrap, 100)
        holder_row.addStretch(1)
        body.setWidget(holder)
        holder.setAutoFillBackground(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header)
        layout.addWidget(body, 1)


    def set_value(self, theme: str, web_search: bool, attachments: bool) -> None:
        self._theme_switch.set_on(theme == "dark")
        self._web_switch.set_on(web_search)
        self._attach_switch.set_on(attachments)


    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self._folder.setIcon(icon("folder", THEMES[theme]["send_text"], SET_ICON_SIZE))
        self.set_models(self._models)
        color = THEMES[theme]["accent_strong"]
        for label, name in self._icons:
            label.setPixmap(icon(name, color, SET_ICON_SIZE).pixmap(QSize(SET_ICON_SIZE, SET_ICON_SIZE)))
        for switch in (self._theme_switch, self._web_switch, self._attach_switch):
            switch.set_theme(theme)


    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.opened.emit()


    def _group(self, text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setObjectName("groupLabel")
        label.setContentsMargins(6, 20, 6, 8)
        return label


    def _models_card(self) -> QFrame:
        self._path = QLineEdit()
        self._path.setObjectName("pathField")
        self._path.setReadOnly(True)
        self._path.setFixedHeight(PATH_ROW_HEIGHT)

        self._folder = QPushButton(ICON_GAP + OPEN_FOLDER_LABEL)
        self._folder.setObjectName("folderBtn")
        self._folder.setFixedHeight(PATH_ROW_HEIGHT)
        self._folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self._folder.setIconSize(QSize(SET_ICON_SIZE, SET_ICON_SIZE))
        self._folder.clicked.connect(self.open_folder_requested)

        path_row = QHBoxLayout()
        path_row.setContentsMargins(0, 0, 0, 14)
        path_row.setSpacing(8)
        path_row.addWidget(self._path, 1)
        path_row.addWidget(self._folder)

        self._found_head = QLabel()
        self._found_head.setObjectName("foundHead")
        self._found_head.setContentsMargins(2, 2, 2, 6)

        found = QWidget()
        self._found = QVBoxLayout(found)
        self._found.setContentsMargins(0, 0, 0, 12)
        self._found.setSpacing(2)

        content = QWidget()
        column = QVBoxLayout(content)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self._set_row("folder", "Priečinok s modelmi", "FUKAI v ňom hľadá súbory .gguf. Nájdené súbory sa ponúknu pri výbere modelu v novom chate.", None))
        column.addLayout(path_row)
        column.addWidget(self._found_head)
        column.addWidget(found)
        return self._card([content])


    @staticmethod
    def _card(rows: list[QWidget]) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        column = QVBoxLayout(card)
        column.setContentsMargins(18, 4, 18, 4)
        column.setSpacing(0)
        for index, row in enumerate(rows):
            if index:
                line = QFrame()
                line.setObjectName("sep")
                column.addWidget(line)
            column.addWidget(row)
        return card


    def _set_row(self, icon_name: str, title: str, desc: str, control: QWidget | None) -> QWidget:
        box = QLabel()
        box.setObjectName("setIcon")
        box.setFixedSize(SET_ICON_BOX, SET_ICON_BOX)
        box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icons.append((box, icon_name))

        head = QLabel(title)
        head.setObjectName("setTitle")
        desc_label = QLabel(desc)
        desc_label.setObjectName("setDesc")
        desc_label.setWordWrap(True)

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(2)
        text.addWidget(head)
        text.addWidget(desc_label)

        row = QWidget()
        line = QHBoxLayout(row)
        line.setContentsMargins(0, 14, 0, 14)
        line.setSpacing(14)
        line.addWidget(box, 0, Qt.AlignmentFlag.AlignTop)
        line.addLayout(text, 1)
        if control is not None:
            line.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        return row


    def _on_theme_toggled(self, on: bool) -> None:
        self.theme_changed.emit("dark" if on else "light")
        self._flash_saved()


    def _on_web_toggled(self, on: bool) -> None:
        self.websearch_changed.emit(on)
        self._flash_saved()


    def _on_attach_toggled(self, on: bool) -> None:
        self.attachments_changed.emit(on)
        self._flash_saved()


    def _flash_saved(self) -> None:
        self._saved.setText(SETTINGS_SAVED_FLASH)
        self._set_flash(True)
        self._saved_timer.start(SETTINGS_SAVED_MS)


    def _clear_flash(self) -> None:
        self._saved.setText(SETTINGS_SAVED_TEXT)
        self._set_flash(False)


    def _set_flash(self, on: bool) -> None:
        self._saved.setProperty("flash", on)
        self._saved.style().unpolish(self._saved)
        self._saved.style().polish(self._saved)


    def set_models_dir(self, path) -> None:
        text = str(path)
        self._path.setText(text)
        self._path.setToolTip(text)
        self._path.setCursorPosition(0)


    def set_models(self, models: list[dict]) -> None:
        self._models = models
        while self._found.count():
            widget = self._found.takeAt(0).widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()
        self._found_head.setText(f"Nájdené modely ({len(models)})")
        if not models:
            empty = QLabel("V priečinku zatiaľ nie je žiadný súbor .gguf (model).")
            empty.setObjectName("foundEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._found.addWidget(empty)
            return
        cube = icon("cube", THEMES[self._theme]["accent_strong"], 16)
        for model in models:
            row = _FoundRow(model, cube)
            row.clicked.connect(self.model_info_requested)
            self._found.addWidget(row)
