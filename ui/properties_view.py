from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, replace
from math import log2
from PyQt6.QtCore import QEvent, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractSpinBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSlider, QSpinBox, QVBoxLayout, QWidget
)
from core.constants import (
    MAX_TOKENS_MAX, MAX_TOKENS_MIN, N_BATCH_MAX, N_BATCH_MIN, N_CTX_MAX, N_CTX_MIN,
    N_GPU_LAYERS_MIN, N_THREADS_MIN, REPEAT_PENALTY_MAX, REPEAT_PENALTY_MIN, SEED_MAX, SEED_MIN,
    PROMPT_RESERVE, TEMPERATURE_MAX, TEMPERATURE_MIN, TOP_K_MAX, TOP_K_MIN,
    TOP_P_MAX, TOP_P_MIN
)
from core.hardware import HardwareProfile
from core.llm_engine import memory_pool
from core.settings import ChatProperties, ModelMeta
from ui.constants import (
    BADGE_LIVE, BADGE_RELOAD, BIG_CONTEXT, CARD_MARGINS, EASY_HINT, EXPERT_LABEL, HEADER_HEIGHT,
    FOOTER_HEIGHT, LAYERS_UNKNOWN_MAX, NUM_HEIGHT, NUM_WIDTH, PARAM_GRID_SPACING, PARAM_MARGINS,
    PARAM_MIN_WIDTH, RANDOM_LABEL, RANDOM_PLACEHOLDER, SEED_NUM_WIDTH,
    PAGE_MAX_WIDTH, PRESET_HEIGHT, PROMPT_BOX_HEIGHT, PROMPT_EMPTY_HINT,
    PROMPT_PRESETS, PROPERTIES_APPLY_LABEL, PROPERTIES_DIRTY, PROPERTIES_NO_MODEL,
    PROPERTIES_NO_MODEL_HINT, PROPERTIES_RELOAD_NOTE, PROPERTIES_RESET_LABEL,
    PROPERTIES_SAVED_FLASH, PROPERTIES_SAVED_MS, PROPERTIES_SAVED_TEXT, PROPERTIES_TITLE,
    SCOPE_CHARS, SEED_FALLBACK, SLIDER_HANDLE, TICK_SPACING
)
from ui.formatting import int_text, pages_text, short_tokens, size_text, tokens_text
from ui.toggle_switch import ToggleSwitch

__all__ = ["PropertiesView"]


def power_steps(start: int, cap: int) -> list[int]:
    steps = []
    value = start
    while value <= cap:
        steps.append(value)
        value *= 2
    if not steps:
        return [cap]
    if steps[-1] != cap:
        steps.append(cap)
    return steps


def ctx_steps(cap: int) -> list[int]:
    return power_steps(N_CTX_MIN, cap)


def _num_text(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}".replace(".", ",") if decimals else int_text(int(value))


def _desc_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("pDesc")
    label.setWordWrap(True)
    label.setContentsMargins(0, 2, 0, 10)
    return label


def _note_label() -> QLabel:
    label = QLabel()
    label.setObjectName("pNote")
    label.setWordWrap(True)
    label.setVisible(False)
    return label


def _layers_tag(value: float) -> str:
    if value == N_GPU_LAYERS_MIN:
        return "všetky na GPU"
    return "len CPU" if value == 0 else "čiastočne na GPU"


@dataclass(frozen=True)
class _Param:
    key: str
    group: str
    label: str
    desc: str
    minimum: float
    maximum: float | None = None
    step: float = 1
    decimals: int = 0
    powers: bool = False
    tag: Callable[[float], str] | None = None
    special: str = ""


PARAMS = (
    _Param("n_gpu_layers", "load", "Vrstvy na GPU",
           "Koľko vrstiev modelu beží na grafickej karte. -1 = všetky (najrýchlejšie), "
           "0 = výpočet len na procesore.",
           N_GPU_LAYERS_MIN, tag=_layers_tag),
    _Param("n_threads", "load", "Vlákna CPU",
           "Počet vlákien pre výpočty na procesore. Predvolene počet výkonných jadier.",
           N_THREADS_MIN),
    _Param("n_batch", "load", "Veľkosť dávky",
           "Koľko tokenov vstupu sa spracuje naraz. Väčšia dávka zrýchli dlhé prompty, "
           "ale zaberie viac pamäte.",
           N_BATCH_MIN, N_BATCH_MAX, powers=True),
    _Param("temperature", "sampling", "Teplota",
           "Nižšia = presnejšie a predvídateľnejšie odpovede, vyššia = kreatívnejšie "
           "a náhodnejšie.",
           TEMPERATURE_MIN, TEMPERATURE_MAX, step=0.05, decimals=2),
    _Param("max_tokens", "sampling", "Max. dĺžka odpovede",
           "Najviac tokenov, ktoré model vygeneruje v jednej odpovedi. Musí sa zmestiť "
           "do kontextu.",
           MAX_TOKENS_MIN, powers=True),
    _Param("top_p", "sampling", "Top-p",
           "Model vyberá len z najpravdepodobnejších tokenov, ktorých súčet "
           "pravdepodobností je p.",
           TOP_P_MIN, TOP_P_MAX, step=0.01, decimals=2),
    _Param("top_k", "sampling", "Top-k",
           "Model vyberá ďalší token len z k najpravdepodobnejších kandidátov.",
           TOP_K_MIN, TOP_K_MAX),
    _Param("repeat_penalty", "sampling", "Penalizácia opakovania",
           "Nad 1,0 potláča opakovanie slov a fráz, 1,0 = bez penalizácie, pod 1,0 "
           "ho podporuje.",
           REPEAT_PENALTY_MIN, REPEAT_PENALTY_MAX, step=0.05, decimals=2),
    _Param("seed", "sampling", "Seed",
           "Rovnaký seed a rovnaké nastavenia dajú rovnakú odpoveď. Hodí sa na testovanie "
           "a porovnávanie.",
           SEED_MIN, SEED_MAX, special="seed"),
)
_PMAP = {param.key: param for param in PARAMS}


def _row_head(label: str, key: str, *right: QWidget) -> QHBoxLayout:
    name = QLabel(label)
    name.setObjectName("pLabel")
    name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    chip = QLabel(key)
    chip.setObjectName("pKey")

    left = QVBoxLayout()
    left.setContentsMargins(0, 0, 0, 0)
    left.setSpacing(3)
    left.addWidget(name)
    left.addWidget(chip, 0, Qt.AlignmentFlag.AlignLeft)

    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    row.addLayout(left, 1)
    for widget in right:
        row.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)
    return row


class _ParamRow(QWidget):
    changed = pyqtSignal(str, object)


    def __init__(self, param: _Param, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.param = param
        self._steps: list[int] | None = None
        self._minimum = param.minimum
        self._maximum = param.maximum if param.maximum is not None else param.minimum

        self._tag = QLabel()
        self._tag.setObjectName("pTag")

        self._num = QDoubleSpinBox() if param.decimals else QSpinBox()
        if param.decimals:
            self._num.setDecimals(param.decimals)
        self._num.setObjectName("num")
        self._num.setFixedSize(NUM_WIDTH, NUM_HEIGHT)
        self._num.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._num.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._num.setKeyboardTracking(False)
        self._num.setSingleStep(param.step)
        self._num.editingFinished.connect(self._on_num)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setSingleStep(1)
        self._slider.setPageStep(1)
        self._slider.valueChanged.connect(self._on_slider)

        self._low = QLabel()
        self._low.setObjectName("pMin")
        self._high = QLabel()
        self._high.setObjectName("pMax")
        self._high.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        slider_row = QHBoxLayout()
        slider_row.setContentsMargins(0, 0, 0, 0)
        slider_row.setSpacing(10)
        slider_row.addWidget(self._low)
        slider_row.addWidget(self._slider, 1)
        slider_row.addWidget(self._high)

        self._note = _note_label()
        self._note.setContentsMargins(0, 10, 0, 0)

        column = QVBoxLayout(self)
        column.setContentsMargins(*PARAM_MARGINS)
        column.setSpacing(0)
        column.addLayout(_row_head(param.label, param.key, self._tag, self._num))
        column.addWidget(_desc_label(param.desc))
        column.addLayout(slider_row)
        column.addWidget(self._note)


    def set_range(self, maximum: float) -> None:
        self._maximum = max(self._minimum, maximum)
        self._steps = power_steps(int(self._minimum), int(self._maximum)) if self.param.powers else None
        self._num.setRange(self._minimum, self._maximum)
        blocked = self._slider.blockSignals(True)
        if self._steps is not None:
            self._slider.setRange(0, len(self._steps) - 1)
        else:
            self._slider.setRange(0, max(1, round((self._maximum - self._minimum) / self.param.step)))
        self._slider.blockSignals(blocked)
        self._low.setText(self._edge(self._minimum))
        self._high.setText(self._edge(self._maximum))


    def set_value(self, value: float) -> None:
        blocked = self._num.blockSignals(True)
        self._num.setValue(value)
        self._num.blockSignals(blocked)
        blocked = self._slider.blockSignals(True)
        self._slider.setValue(self._index_of(value))
        self._slider.blockSignals(blocked)
        self._tag.setText(self.param.tag(value) if self.param.tag else "")


    def set_note(self, text: str) -> None:
        self._note.setText(text)
        self._note.setVisible(bool(text))


    def value(self) -> float:
        return self._num.value()


    def _edge(self, value: float) -> str:
        return short_tokens(int(value)) if self.param.powers else _num_text(value, self.param.decimals)


    def _index_of(self, value: float) -> int:
        if self._steps is not None:
            target = log2(max(1, value))
            return min(range(len(self._steps)), key=lambda i: abs(log2(max(1, self._steps[i])) - target))
        return round((value - self._minimum) / self.param.step)


    def _value_of(self, index: int) -> float:
        if self._steps is not None:
            return self._steps[max(0, min(len(self._steps) - 1, index))]
        value = self._minimum + index * self.param.step
        return round(value, self.param.decimals) if self.param.decimals else int(round(value))


    def _on_slider(self, index: int) -> None:
        self._emit(self._value_of(index))


    def _on_num(self) -> None:
        value = self._num.value()
        self._emit(round(value, self.param.decimals) if self.param.decimals else int(value))


    def _emit(self, value: float) -> None:
        self.set_value(value)
        self.changed.emit(self.param.key, value)


class _SeedRow(QWidget):
    changed = pyqtSignal(str, object)


    def __init__(self, param: _Param, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.param = param
        self._value: int | None = None

        caption = QLabel(RANDOM_LABEL)
        caption.setObjectName("miniLabel")
        self._switch = ToggleSwitch()
        self._switch.toggled.connect(self._on_switch)

        self._edit = QLineEdit()
        self._edit.setObjectName("num")
        self._edit.setFixedSize(SEED_NUM_WIDTH, NUM_HEIGHT)
        self._edit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._edit.setPlaceholderText(RANDOM_PLACEHOLDER)
        self._edit.editingFinished.connect(self._on_edit)

        column = QVBoxLayout(self)
        column.setContentsMargins(*PARAM_MARGINS)
        column.setSpacing(0)
        column.addLayout(_row_head(param.label, param.key, caption, self._switch, self._edit))
        column.addWidget(_desc_label(param.desc))


    def set_value(self, value: int | None) -> None:
        self._value = value
        self._switch.set_on(value is None)
        self._edit.setEnabled(value is not None)
        blocked = self._edit.blockSignals(True)
        self._edit.setText("" if value is None else str(value))
        self._edit.blockSignals(blocked)


    def set_range(self, maximum: float) -> None:
        return None


    def set_note(self, text: str) -> None:
        return None


    def set_theme(self, theme: str) -> None:
        self._switch.set_theme(theme)


    def _on_switch(self, random: bool) -> None:
        value = None if random else (self._value if self._value is not None else SEED_FALLBACK)
        self.set_value(value)
        self.changed.emit(self.param.key, value)


    def _on_edit(self) -> None:
        text = self._edit.text().strip()
        if not text:
            self.set_value(None)
        else:
            try:
                self.set_value(max(SEED_MIN, min(SEED_MAX, int(text))))
            except ValueError:
                self.set_value(self._value)        # nečíslo - vrátime poslednú platnú hodnotu
                return
        self.changed.emit(self.param.key, self._value)


class _Grid(QWidget):
    def __init__(self, min_width: int, spacing: tuple[int, int], align: Qt.AlignmentFlag | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._min_width = min_width
        self._align = align
        self._items: list[QWidget] = []
        self._columns = 0
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(spacing[0])
        self._grid.setVerticalSpacing(spacing[1])


    def set_items(self, widgets: list[QWidget]) -> None:
        self._items = widgets
        for widget in widgets:
            widget.setParent(self)
        self._columns = 0
        self._reflow()


    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow()


    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        return QSize(min(self._min_width, hint.width()), hint.height())


    def _reflow(self) -> None:
        if not self._items:
            return
        columns = max(1, min(len(self._items), self.width() // self._min_width))
        if columns == self._columns:
            return
        self._columns = columns
        for widget in self._items:
            self._grid.removeWidget(widget)
        for index, widget in enumerate(self._items):
            if self._align is None:
                self._grid.addWidget(widget, index // columns, index % columns)
            else:
                self._grid.addWidget(widget, index // columns, index % columns, self._align)
        for column in range(self._grid.columnCount()):
            self._grid.setColumnStretch(column, 1 if column < columns else 0)
        self.updateGeometry()


class _Elided(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)


    def set_full_text(self, text: str) -> None:
        self._full = text
        self._apply()


    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply()


    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._apply()


    def _apply(self) -> None:
        self.setText(self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight,
                                                   max(0, self.width())))


class _Ticks(QWidget):
    clicked = pyqtSignal(int)


    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._labels: list[QLabel] = []
        self._current = -1
        self.setCursor(Qt.CursorShape.PointingHandCursor)


    def set_labels(self, texts: list[str]) -> None:
        for label in self._labels:
            label.hide()
            label.deleteLater()
        self._labels = []
        for text in texts:
            label = QLabel(text, self)
            label.setObjectName("tick")
            label.setProperty("on", False)
            label.adjustSize()
            label.show()
            self._labels.append(label)
        self._current = -1
        self.setFixedHeight(max((label.height() for label in self._labels), default=0) + TICK_SPACING)
        self._place()


    def set_current(self, index: int) -> None:
        if index == self._current:
            return
        self._current = index
        for position, label in enumerate(self._labels):
            label.setProperty("on", position == index)
            label.style().unpolish(label)
            label.style().polish(label)
            label.adjustSize()      # tučný popis je širší, inak by sedel mimo stredu
        self._place()


    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place()


    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            for label in self._labels:
                label.adjustSize()
            self._place()


    def mousePressEvent(self, event) -> None:
        if len(self._labels) > 1:
            span = max(1, self.width() - SLIDER_HANDLE)
            ratio = (event.position().x() - SLIDER_HANDLE / 2) / span
            index = round(ratio * (len(self._labels) - 1))
            self.clicked.emit(max(0, min(len(self._labels) - 1, index)))
        super().mousePressEvent(event)


    def _place(self) -> None:
        if len(self._labels) < 2:
            return
        span = self.width() - SLIDER_HANDLE
        for index, label in enumerate(self._labels):
            center = SLIDER_HANDLE / 2 + span * index / (len(self._labels) - 1)
            x = round(center - label.width() / 2)
            label.move(max(0, min(self.width() - label.width(), x)), TICK_SPACING)


class PropertiesView(QWidget):
    apply_requested = pyqtSignal(object)
    opened = pyqtSignal()


    def __init__(self, hardware: HardwareProfile, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hardware = hardware
        self._props: ChatProperties | None = None
        self._applied: ChatProperties | None = None
        self._model: dict | None = None
        self._meta: ModelMeta | None = None
        self._steps = ctx_steps(N_CTX_MAX)
        self._clamped_ctx = False
        self._free_mb: int | None = None
        self._pool = ""
        self._busy = False
        self._expert_only: list[QWidget] = []
        self._easy_only: list[QWidget] = []
        self._rows: dict[str, _ParamRow | _SeedRow] = {}

        self._flash = QTimer(self)
        self._flash.setSingleShot(True)
        self._flash.timeout.connect(self._update_apply)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_header())
        layout.addWidget(self._build_body(), 1)
        layout.addWidget(self._build_footer())
        self.set_expert(False)
        self._update_apply()


    def load(self, props: ChatProperties | None, *, chat_title: str | None, model: dict | None) -> None:
        self._model = model
        self._meta = ModelMeta.from_dict(model["meta"]) if model and model.get("meta") else None
        self._applied = props
        self._props = props
        self._free_mb, self._pool = self._measure_pool(props)

        scope = self._scope_text(chat_title, model)
        self._scope.set_full_text(scope)
        self._scope.setToolTip(chat_title or scope)
        self._set_steps()
        self._hw_line.setText(self._hardware_text())
        self._fill()
        self._update_apply()


    def confirm_applied(self) -> None:
        reload_needed = self._applied is not None and self._props is not None and self._applied.needs_reload(self._props)
        self._applied = self._props
        self._clamped_ctx = False
        self._update_apply()
        self._status.setText(PROPERTIES_SAVED_FLASH + (f" · {PROPERTIES_RELOAD_NOTE}" if reload_needed else ""))
        self._set_state("ok")
        self._flash.start(PROPERTIES_SAVED_MS)


    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._update_apply()


    def set_expert(self, expert: bool) -> None:
        self._expert.set_on(expert)
        for widget in self._expert_only:
            widget.setVisible(expert)
        for widget in self._easy_only:
            widget.setVisible(not expert)


    def set_theme(self, theme: str) -> None:
        self._expert.set_theme(theme)
        for row in self._rows.values():
            if isinstance(row, _SeedRow):
                row.set_theme(theme)


    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.opened.emit()


    def _build_header(self) -> QFrame:
        title = QLabel(PROPERTIES_TITLE)
        title.setObjectName("headTitle")
        title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        self._scope = _Elided()
        self._scope.setObjectName("scopeText")
        self._scope.set_full_text(PROPERTIES_NO_MODEL)
        chip = QFrame()
        chip.setObjectName("scopeChip")
        chip.setMaximumHeight (28)
        chip_row = QHBoxLayout(chip)
        chip_row.setContentsMargins(10, 4, 10, 4)
        chip_row.addWidget(self._scope)

        mode = QLabel(EXPERT_LABEL)
        mode.setObjectName("modeLabel")
        self._expert = ToggleSwitch()
        self._expert.toggled.connect(self.set_expert)

        header = QFrame()
        header.setObjectName("propertiesHeader")
        header.setFixedHeight(HEADER_HEIGHT)
        row = QHBoxLayout(header)
        row.setContentsMargins(20, 0, 20, 0)
        row.setSpacing(12)
        row.addWidget(title, 2)
        row.addWidget(chip, 3)
        row.addSpacing(8)
        row.addWidget(mode)
        row.addWidget(self._expert)
        return header


    def _build_body(self) -> QScrollArea:
        self._wrap = QWidget()
        self._wrap.setObjectName("settingsWrap")
        self._wrap.setMaximumWidth(PAGE_MAX_WIDTH)
        column = QVBoxLayout(self._wrap)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self._group("Správanie asistenta"))
        column.addWidget(self._prompt_card())
        column.addWidget(self._group("Pamäť konverzácie", BADGE_RELOAD))
        column.addWidget(self._ctx_card())
        column.addWidget(self._only_expert(self._group("Hardvér a načítanie", BADGE_RELOAD)))
        column.addWidget(self._only_expert(self._load_card()))
        column.addWidget(self._only_expert(self._group("Generovanie odpovede", BADGE_LIVE, "live")))
        column.addWidget(self._only_expert(self._sampling_card()))
        column.addWidget(self._only_easy(self._easy_hint()))
        column.addStretch(1)

        body = QScrollArea()
        body.setObjectName("propertiesBody")
        body.setWidgetResizable(True)
        body.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        holder = QWidget()
        holder_row = QHBoxLayout(holder)
        holder_row.setContentsMargins(24, 8, 24, 24)
        holder_row.addStretch(1)
        holder_row.addWidget(self._wrap, 100)
        holder_row.addStretch(1)
        body.setWidget(holder)
        holder.setAutoFillBackground(False)
        return body


    def _build_footer(self) -> QFrame:
        self._status = QLabel()
        self._status.setObjectName("applyStatus")
        self._status.setProperty("state", "")
        self._status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        self._reset = QPushButton(PROPERTIES_RESET_LABEL)
        self._reset.setObjectName("ghostBtn")
        self._reset.setFixedHeight(38)
        self._reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset.clicked.connect(self._on_reset)

        self._apply = QPushButton(PROPERTIES_APPLY_LABEL)
        self._apply.setObjectName("applyBtn")
        self._apply.setFixedHeight(38)
        self._apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply.clicked.connect(self._on_apply)

        footer = QFrame()
        footer.setObjectName("propertiesFooter")
        footer.setFixedHeight(FOOTER_HEIGHT)
        row = QHBoxLayout(footer)
        row.setContentsMargins(24, 0, 24, 0)
        row.setSpacing(10)
        row.addWidget(self._status, 1)
        row.addWidget(self._reset)
        row.addWidget(self._apply)
        return footer


    def _group(self, text: str, badge: str | None = None, kind: str = "reload") -> QWidget:
        label = QLabel(text.upper())
        label.setObjectName("groupLabel")

        row = QWidget()
        line = QHBoxLayout(row)
        line.setContentsMargins(6, 20, 6, 8)
        line.setSpacing(8)
        line.addWidget(label)
        if badge is not None:
            tag = QLabel(badge)
            tag.setObjectName("badge")
            tag.setProperty("kind", kind)
            line.addWidget(tag)
            self._expert_only.append(tag)
        line.addStretch(1)
        return row


    @staticmethod
    def _card(rows: list[QWidget | QHBoxLayout]) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        column = QVBoxLayout(card)
        column.setContentsMargins(*CARD_MARGINS)
        column.setSpacing(0)
        for row in rows:
            if isinstance(row, QWidget):
                column.addWidget(row)
            else:
                column.addLayout(row)
        return card


    def _head(self, label: str, key: str, *right: QWidget) -> QHBoxLayout:
        name = QLabel(label)
        name.setObjectName("pLabel")
        name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        chip = QLabel(key)
        chip.setObjectName("pKey")
        self._expert_only.append(chip)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(name)
        row.addWidget(chip)
        row.addStretch(1)
        for widget in right:
            row.addWidget(widget)
        return row


    def _prompt_card(self) -> QFrame:
        self._prompt_hint = QLabel()
        self._prompt_hint.setObjectName("pHint")

        self._prompt = QPlainTextEdit()
        self._prompt.setObjectName("promptBox")
        self._prompt.setFixedHeight(PROMPT_BOX_HEIGHT)
        self._prompt.setTabChangesFocus(True)
        self._prompt.textChanged.connect(self._on_prompt_changed)

        presets = _Grid(160, (6, 6), Qt.AlignmentFlag.AlignLeft)
        presets.setContentsMargins(0, 10, 0, 0)
        buttons = []
        for name in PROMPT_PRESETS:
            button = QPushButton(name)
            button.setObjectName("preset")
            button.setFixedHeight(PRESET_HEIGHT)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, key=name: self._on_preset(key))
            buttons.append(button)
        presets.set_items(buttons)

        return self._card([
            self._head("Systémový prompt", "system_prompt", self._prompt_hint),
            _desc_label("Úvodný pokyn, ktorý model dostane pred každou konverzáciou. Určuje jeho rolu, "
                       "tón a jazyk odpovedí."),
            self._prompt,
            presets,
        ])


    def _ctx_card(self) -> QFrame:
        self._ctx_tag = QLabel()
        self._ctx_tag.setObjectName("pTag")

        self._ctx_num = QSpinBox()
        self._ctx_num.setObjectName("num")
        self._ctx_num.setFixedSize(NUM_WIDTH, NUM_HEIGHT)
        self._ctx_num.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._ctx_num.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self._ctx_num.setKeyboardTracking(False)
        self._ctx_num.setRange(N_CTX_MIN, N_CTX_MAX)
        self._ctx_num.editingFinished.connect(lambda: self._set_ctx(self._ctx_num.value()))
        self._expert_only.append(self._ctx_num)

        self._ctx_slider = QSlider(Qt.Orientation.Horizontal)
        self._ctx_slider.setObjectName("ctxSlider")
        self._ctx_slider.setSingleStep(1)
        self._ctx_slider.setPageStep(1)
        self._ctx_slider.valueChanged.connect(self._on_ctx_step)

        self._ticks = _Ticks()
        self._ticks.clicked.connect(self._on_ctx_step)

        self._memory = QLabel()
        self._memory.setObjectName("pMemory")
        self._memory.setWordWrap(True)
        self._memory.setContentsMargins(0, 10, 0, 0)

        self._ctx_note = QLabel()
        self._ctx_note.setObjectName("pNote")
        self._ctx_note.setWordWrap(True)
        self._ctx_note.setContentsMargins(0, 10, 0, 0)
        self._ctx_note.setVisible(False)

        return self._card([
            self._head("Max. kontext", "n_ctx", self._ctx_tag, self._ctx_num),
            _desc_label("Koľko textu si model pamätá naraz: systémový prompt, história chatu, prílohy aj "
                       "samotná odpoveď. Viac kontextu zaberie viac pamäte a model sa načíta pomalšie."),
            self._ctx_slider,
            self._ticks,
            self._memory,
            self._ctx_note,
        ])


    def _only_expert(self, widget: QWidget) -> QWidget:
        self._expert_only.append(widget)
        return widget


    def _only_easy(self, widget: QWidget) -> QWidget:
        self._easy_only.append(widget)
        return widget


    def _row(self, param: _Param) -> QWidget:
        row = _SeedRow(param) if param.special == "seed" else _ParamRow(param)
        row.changed.connect(self._on_param)
        self._rows[param.key] = row
        return row


    def _param_grid(self, group: str) -> _Grid:
        grid = _Grid(PARAM_MIN_WIDTH, PARAM_GRID_SPACING)
        grid.set_items([self._row(param) for param in PARAMS if param.group == group])
        return grid


    def _load_card(self) -> QFrame:
        dot = QLabel()
        dot.setObjectName("hwDot")
        dot.setFixedSize(8, 8)
        self._hw_line = QLabel()
        self._hw_line.setObjectName("hwText")
        self._hw_line.setWordWrap(True)

        line = QWidget()
        row = QHBoxLayout(line)
        row.setContentsMargins(0, 0, 0, 4)
        row.setSpacing(8)
        row.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self._hw_line, 1)
        return self._card([line, self._param_grid("load")])


    def _sampling_card(self) -> QFrame:
        return self._card([self._param_grid("sampling")])


    @staticmethod
    def _easy_hint() -> QLabel:
        hint = QLabel(EASY_HINT)
        hint.setObjectName("easyHint")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setContentsMargins(0, 18, 0, 0)
        return hint


    def _set_steps(self) -> None:
        cap = N_CTX_MAX
        if self._meta is not None and self._meta.n_ctx_train:
            cap = min(cap, max(N_CTX_MIN, self._meta.n_ctx_train))
        self._steps = ctx_steps(cap)
        self._ctx_num.setRange(N_CTX_MIN, self._steps[-1])
        blocked = self._ctx_slider.blockSignals(True)
        self._ctx_slider.setRange(0, len(self._steps) - 1)
        self._ctx_slider.blockSignals(blocked)
        self._ticks.set_labels([short_tokens(step) for step in self._steps])


    def _fill(self) -> None:
        props = self._props
        blocked = self._prompt.blockSignals(True)
        self._prompt.setPlainText("" if props is None else props.chat.system_prompt)
        self._prompt.blockSignals(blocked)
        self._sync_prompt_hint()

        self._clamped_ctx = False
        if props is not None:
            n_ctx = min(props.load.n_ctx, self._steps[-1])
            if n_ctx != props.load.n_ctx:
                self._clamped_ctx = True
                self._props = replace(props, load=replace(props.load, n_ctx=n_ctx))
            self._show_ctx(n_ctx)
        self._sync_ctx()
        for key in self._rows:
            self._sync_param(key)


    def _show_ctx(self, value: int) -> None:
        blocked = self._ctx_slider.blockSignals(True)
        self._ctx_slider.setValue(self._nearest(value))
        self._ctx_slider.blockSignals(blocked)
        blocked = self._ctx_num.blockSignals(True)
        self._ctx_num.setValue(value)
        self._ctx_num.blockSignals(blocked)


    def _nearest(self, value: int) -> int:
        target = log2(max(1, value))
        return min(range(len(self._steps)), key=lambda index: abs(log2(self._steps[index]) - target))


    def _measure_pool(self, props: ChatProperties | None) -> tuple[int | None, str]:
        if props is None:
            return None, ""
        free_mb, where = memory_pool(props.load, self._hardware.gpu_offload)
        return (free_mb if free_mb else None), where


    def _sync_ctx(self) -> None:
        if self._props is None:
            self._ctx_tag.setText("")
            self._memory.setText("")
            self._set_note("")
            return
        n_ctx = self._props.load.n_ctx
        self._ctx_tag.setText(f"{int_text(n_ctx)} tokenov · {pages_text(n_ctx)} textu")
        self._ticks.set_current(self._nearest(n_ctx))

        size_mb = self._model.get("size_mb") if self._model else None
        kv_mb = self._meta.kv_cache_mb(n_ctx) if self._meta else None
        need_mb = size_mb + kv_mb if size_mb and kv_mb is not None else None
        if need_mb is None:
            self._memory.setText(f"Model {size_text(size_mb)}" if size_mb else "")
        else:
            text = f"Model {size_text(size_mb)} + kontext {size_text(kv_mb)} = {size_text(need_mb)}"
            if self._free_mb:
                text += f" · voľných {size_text(self._free_mb)} {self._pool}"
            self._memory.setText(text)

        if self._clamped_ctx:
            self._set_note(f"Model zvládne najviac {int_text(self._steps[-1])} tokenov, "
                           f"uložená hodnota bola vyššia a zmenšila sa.")
        elif need_mb is not None and self._free_mb and need_mb > self._free_mb:
            self._set_note(f"Model s týmto kontextom potrebuje viac {self._pool}, než je voľnej. "
                           f"Načítanie môže zlyhať alebo byť veľmi pomalé.")
        elif n_ctx >= BIG_CONTEXT:
            self._set_note("Veľký kontext potrebuje veľa pamäte a model sa bude načítavať dlhšie.")
        else:
            self._set_note("")


    def _set_note(self, text: str) -> None:
        self._ctx_note.setText(text)
        self._ctx_note.setVisible(bool(text))


    def _sync_prompt_hint(self) -> None:
        text = self._prompt.toPlainText()
        if not text.strip():
            self._prompt_hint.setText(PROMPT_EMPTY_HINT)
            return
        self._prompt_hint.setText(tokens_text(_approx_tokens(text)))


    def _on_prompt_changed(self) -> None:
        self._sync_prompt_hint()
        if self._props is None:
            return
        self._props = replace(self._props, chat=replace(self._props.chat, system_prompt=self._prompt.toPlainText()))
        self._update_apply()


    def _on_preset(self, name: str) -> None:
        self._prompt.setPlainText(PROMPT_PRESETS[name])


    def _on_ctx_step(self, index: int) -> None:
        self._set_ctx(self._steps[max(0, min(len(self._steps) - 1, index))])


    def _set_ctx(self, value: int) -> None:
        if self._props is None or value == self._props.load.n_ctx:
            return
        self._clamped_ctx = False
        self._props = replace(self._props, load=replace(self._props.load, n_ctx=value))
        self._show_ctx(value)
        self._sync_ctx()
        self._sync_param("max_tokens")
        self._update_apply()


    def _on_reset(self) -> None:
        if self._props is None:
            return
        self._props = ChatProperties.defaults_for(self._props.load.model_path, self._hardware, meta=self._meta)
        self._fill()
        self._update_apply()


    def _on_apply(self) -> None:
        if self._props is not None:
            self.apply_requested.emit(self._props)


    def _maximum(self, param: _Param) -> float:
        if param.key == "n_gpu_layers":
            layers = self._meta.n_layers if self._meta is not None else None
            return layers + 1 if layers else LAYERS_UNKNOWN_MAX
        if param.key == "n_threads":
            return max(N_THREADS_MIN, self._hardware.cores_logical)
        if param.key == "max_tokens":
            n_ctx = self._props.load.n_ctx if self._props is not None else N_CTX_MAX
            return min(MAX_TOKENS_MAX, n_ctx)
        return param.maximum if param.maximum is not None else param.minimum


    def _sync_param(self, key: str) -> None:
        row = self._rows[key]
        if self._props is None:
            return
        param = row.param
        value = getattr(self._props.load if param.group == "load" else self._props.sampling, key)
        if key == "n_threads" and value is None:
            value = self._hardware.n_threads      # None = nech rozhodne llama.cpp, ukazujeme odhad
        if param.special != "seed":
            maximum = self._maximum(param)
            row.set_range(maximum)
            if value > maximum:
                value = maximum
                self._store(param, value)
        row.set_value(value)
        if key == "max_tokens":
            row.set_note(self._max_tokens_note(value))


    def _store(self, param: _Param, value) -> None:
        if param.group == "load":
            self._props = replace(self._props, load=replace(self._props.load, **{param.key: value}))
        else:
            self._props = replace(self._props, sampling=replace(self._props.sampling, **{param.key: value}))


    def _on_param(self, key: str, value) -> None:
        if self._props is None:
            return
        self._store(_PMAP[key], value)
        if key == "n_gpu_layers":
            self._free_mb, self._pool = self._measure_pool(self._props)
            self._sync_ctx()
        if key == "max_tokens":
            self._rows[key].set_note(self._max_tokens_note(value))
        self._update_apply()


    def _max_tokens_note(self, value: int) -> str:
        if self._props is None:
            return ""
        rest = self._props.load.n_ctx - value - PROMPT_RESERVE
        if rest <= 0:
            return "Odpoveď sa do kontextu nezmestí. Zníž jej dĺžku, alebo zvýš kontext."
        if value * 2 >= self._props.load.n_ctx:
            return f"Na otázku, prílohy a históriu zostane z kontextu {int_text(rest)} tokenov."
        return ""


    def _hardware_text(self) -> str:
        hardware = self._hardware
        parts = []
        if hardware.backend == "cpu":
            parts.append("Výpočet na procesore")
        elif hardware.gpu is not None:
            vram = hardware.gpu.vram_total_mb
            name = hardware.gpu.name.removeprefix("NVIDIA ").removeprefix("GeForce ")
            parts.append(f"{name} · {vram // 1024} GB VRAM" if vram else name)
        parts.append(f"CPU {hardware.cores_performance} výkonných jadier z {hardware.cores_logical}")
        layers = self._meta.n_layers if self._meta is not None else None
        parts.append(f"model má {layers} vrstiev" if layers else "počet vrstiev modelu nie je známy")
        return "Detegované: " + " · ".join(parts)


    def _changes(self) -> tuple[int, bool]:
        applied, props = self._applied.to_dict(), self._props.to_dict()
        count = sum(1 for group in applied for key in applied[group] if applied[group][key] != props[group][key])
        return count, self._applied.needs_reload(self._props)


    def _update_apply(self) -> None:
        enabled = self._props is not None and not self._busy
        self._wrap.setEnabled(enabled)
        self._reset.setEnabled(enabled)

        if self._props is None or self._applied is None:
            self._status.setText(PROPERTIES_NO_MODEL_HINT)
            self._set_state("")
            self._apply.setEnabled(False)
            return

        count, reload_needed = self._changes()
        self._apply.setEnabled(bool(count) and enabled)
        if not count:
            self._status.setText(PROPERTIES_SAVED_TEXT)
            self._set_state("")
            return
        text = f"{PROPERTIES_DIRTY} ({count})"
        if reload_needed:
            text += f" · {PROPERTIES_RELOAD_NOTE}"
        self._status.setText(text)
        self._set_state("dirty")


    def _set_state(self, state: str) -> None:
        self._status.setProperty("state", state)
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)


    @staticmethod
    def _scope_text(chat_title: str | None, model: dict | None) -> str:
        if model is None:
            return PROPERTIES_NO_MODEL
        if chat_title is None:
            return f"Predvolené pre nový chat · {model['title']}"
        short = chat_title if len(chat_title) <= SCOPE_CHARS else chat_title[:SCOPE_CHARS] + "…"
        return f"Chat: {short} · {model['title']}"


def _approx_tokens(text: str) -> int:
    return max(1, round(len(text) / 4))
