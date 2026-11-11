from __future__ import annotations
from math import ceil
from PyQt6.QtCore import QEvent, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFontMetricsF
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QToolButton, QWidget
)
from extensions.file_parser import Attachment
from ui.constants import (
    CHIP_TRIMMED,
    CHIP_BUTTON, CHIP_CLOSE, CHIP_HEIGHT, CHIP_MIN_WIDTH, CHIP_NAME_MAX, CHIP_NAME_MIN,
    CHIP_PENDING, CHIP_ROWS_VISIBLE, CHIP_SPACING
)
from ui.formatting import approx_tokens, int_text, tokens_text

__all__ = ["AttachmentBar", "ChipName"]


class ChipName(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("chipName")
        self._full = text
        self._apply()


    def sizeHint(self) -> QSize:
        width = min(ceil(QFontMetricsF(self.font()).horizontalAdvance(self._full)), CHIP_NAME_MAX)
        return QSize(width, super().sizeHint().height())


    def minimumSizeHint(self) -> QSize:
        return QSize(CHIP_NAME_MIN, super().minimumSizeHint().height())


    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply()


    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self.updateGeometry()
            self._apply()


    def _apply(self) -> None:
        metrics = self.fontMetrics()
        self.setText(metrics.elidedText(self._full, Qt.TextElideMode.ElideMiddle, max(0, self.width())))


class _Chip(QFrame):
    remove_requested = pyqtSignal(int)
    clicked = pyqtSignal(int)


    def __init__(self, job_id: int, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("chip")
        self.job_id = job_id
        self.title = title
        self.item: Attachment | None = None
        self.setFixedHeight(CHIP_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._name = ChipName(title)
        self._meta = QLabel(CHIP_PENDING)
        self._meta.setObjectName("chipMeta")

        self._close = QToolButton()
        self._close.setObjectName("chipClose")
        self._close.setFixedSize(CHIP_BUTTON, CHIP_BUTTON)
        self._close.setText(CHIP_CLOSE)
        self._close.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close.setToolTip("Odobrať prílohu")
        self._close.clicked.connect(lambda: self.remove_requested.emit(self.job_id))

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 10, 0)
        row.setSpacing(6)
        row.addWidget(self._name, 1)
        row.addWidget(self._meta)
        row.addWidget(self._close)
        self.setToolTip(title)


    def set_ready(self, item: Attachment) -> None:
        self.item = item
        label = tokens_text(approx_tokens(item.text))
        self._meta.setText(f"{label} · {CHIP_TRIMMED}" if item.trimmed else label)
        self.setToolTip(f"{item.title}\n{int_text(item.chars)} znakov · kliknutím zobrazíš text")


    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.item is not None:
            self.clicked.emit(self.job_id)
        super().mouseReleaseEvent(event)


class AttachmentBar(QScrollArea):
    removed = pyqtSignal(int)
    preview_requested = pyqtSignal(object)
    changed = pyqtSignal()


    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("attachmentBar")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self._chips: dict[int, _Chip] = {}
        self._restored = 0
        self._theme = "light"
        self._placed: tuple = ()

        content = QWidget()
        self._grid = QGridLayout(content)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(CHIP_SPACING[0])
        self._grid.setVerticalSpacing(CHIP_SPACING[1])
        self.setWidget(content)
        content.setAutoFillBackground(False)
        self.viewport().setAutoFillBackground(False)
        self.setVisible(False)


    def add(self, job_id: int, title: str) -> None:
        chip = _Chip(job_id, title, self.widget())
        chip.remove_requested.connect(self.remove)
        chip.clicked.connect(self._on_clicked)
        self._chips[job_id] = chip
        self._reflow()
        QTimer.singleShot(0, lambda: self._reveal(job_id))
        self.changed.emit()


    def set_ready(self, job_id: int, item: Attachment) -> None:
        chip = self._chips.get(job_id)
        if chip is not None:
            chip.set_ready(item)
            self._reflow()
            self.changed.emit()


    def remove(self, job_id: int) -> None:
        chip = self._chips.pop(job_id, None)
        if chip is None:
            return
        self._drop(chip)
        self._reflow()
        self.removed.emit(job_id)
        self.changed.emit()


    def attachments(self) -> list[Attachment]:
        return [chip.item for chip in self._chips.values() if chip.item is not None]


    def pending(self) -> int:
        return sum(1 for chip in self._chips.values() if chip.item is None)


    def restore(self, items: list[Attachment]) -> None:
        for item in items:
            self._restored -= 1
            self.add(self._restored, item.title)
            self.set_ready(self._restored, item)


    def clear(self) -> None:
        while self._chips:
            _, chip = self._chips.popitem()
            self._drop(chip)
        self._reflow()
        self.changed.emit()


    def set_theme(self, theme: str) -> None:
        self._theme = theme


    def _drop(self, chip: _Chip) -> None:
        self._grid.removeWidget(chip)
        chip.hide()
        chip.deleteLater()


    def _on_clicked(self, job_id: int) -> None:
        chip = self._chips.get(job_id)
        if chip is not None and chip.item is not None:
            self.preview_requested.emit(chip.item)
    
    
    def _reveal(self, job_id: int) -> None:
        chip = self._chips.get(job_id)
        if chip is not None:
            self.ensureWidgetVisible(chip, 0, 0)


    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow()


    def _reflow(self) -> None:
        chips = list(self._chips.values())
        self.setVisible(bool(chips))
        if not chips:
            self._placed = ()
            return
        for chip in chips:
            chip.ensurePolished()
        cell = max(CHIP_MIN_WIDTH, *(chip.minimumSizeHint().width() for chip in chips))
        spacing = CHIP_SPACING[0]
        columns = max(1, min(len(chips), (self.viewport().width() + spacing) // (cell + spacing)))
        placed = (tuple(self._chips), columns, cell)
        if placed != self._placed:
            self._placed = placed
            for chip in chips:
                self._grid.removeWidget(chip)
            for index, chip in enumerate(chips):
                self._grid.addWidget(chip, index // columns, index % columns)
            for column in range(max(self._grid.columnCount(), columns + 1)):
                self._grid.setColumnMinimumWidth(column, cell if column < columns else 0)
                self._grid.setColumnStretch(column, 1 if column == columns else 0)
        rows = min(-(-len(chips) // columns), CHIP_ROWS_VISIBLE)
        self.setFixedHeight(rows * CHIP_HEIGHT + (rows - 1) * CHIP_SPACING[1])
