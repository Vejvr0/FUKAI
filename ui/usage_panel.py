from __future__ import annotations
from PyQt6.QtCore import QEvent, QTimer
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from core.monitor import Usage, UsageMonitor
from ui.constants import USAGE_INTERVAL_MS, USAGE_WIDEST

__all__ = ["UsagePanel"]


def _value(value: float | None) -> str:
    return "–" if value is None else f"{value:.0f} %"


class UsagePanel(QFrame):
    def __init__(self, monitor: UsageMonitor, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("usagePanel")
        self._monitor = monitor

        self._rows = []
        column = QVBoxLayout(self)
        column.setContentsMargins(8, 0, 8, 0)
        column.setSpacing(0)
        for _ in range(3):
            label = QLabel()
            label.setObjectName("usageText")
            self._rows.append(label)
            column.addWidget(label)

        self._timer = QTimer(self)
        self._timer.setInterval(USAGE_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)
        self.set_usage(Usage(memory_label=monitor.memory_label))
        self.hide()

    def toggle(self) -> None:
        self.setVisible(not self.isVisible())

    def setVisible(self, visible: bool) -> None:
        super().setVisible(visible)
        if visible:
            self._tick()
            self._timer.start()
        else:
            self._timer.stop()

    def set_usage(self, usage: Usage) -> None:
        values = ((f"CPU: {_value(usage.cpu)}"),
                  (f"GPU: {_value(usage.gpu)}"),
                  (f"{usage.memory_label}: {_value(usage.memory)}"))
        for label, text in zip(self._rows, values):
            label.setText(text)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._fit()

    def _fit(self) -> None:
        margins = self.layout().contentsMargins()
        width = self._rows[0].fontMetrics().horizontalAdvance(USAGE_WIDEST)
        self.setFixedWidth(width + margins.left() + margins.right())

    def _tick(self) -> None:
        self.set_usage(self._monitor.sample())
