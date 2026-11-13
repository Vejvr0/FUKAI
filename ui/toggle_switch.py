# --- ./ui/toggle_switch.py ---


from __future__ import annotations
from PyQt6.QtWidgets import QAbstractButton, QWidget
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPen
from ui.constants import ICON_DISABLED_OPACITY, SWITCH_ANIM_MS, SWITCH_HEIGHT, SWITCH_KNOB, SWITCH_WIDTH
from ui.style import THEMES, qcolor

__all__ = ["ToggleSwitch"]

KNOB_COLOR = QColor("#FFFFFF")
KNOB_SHADOW = QColor(0, 0, 0, 70)


class ToggleSwitch(QAbstractButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(SWITCH_WIDTH, SWITCH_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._offset = 0.0
        self._track_off = QColor()
        self._track_on = QColor()
        self._border = QColor()

        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(SWITCH_ANIM_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.toggled.connect(self._animate)
        self.set_theme("light")


    @pyqtProperty(float)
    def offset(self) -> float:
        return self._offset


    @offset.setter
    def offset(self, value: float) -> None:
        self._offset = value
        self.update()


    def set_theme(self, theme: str) -> None:
        tokens = THEMES[theme]
        self._track_off = qcolor(tokens["chip_hover"])
        self._track_on = qcolor(tokens["accent"])
        self._border = qcolor(tokens["line"])
        self.update()


    def set_on(self, on: bool) -> None:
        if on == self.isChecked():
            return
        blocked = self.blockSignals(True)
        self.setChecked(on)
        self.blockSignals(blocked)
        self._anim.stop()
        self.offset = 1.0 if on else 0.0


    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()


    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(ICON_DISABLED_OPACITY)

        track = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        radius = track.height() / 2
        painter.setBrush(self._track_on if self.isChecked() else self._track_off)
        painter.setPen(Qt.PenStyle.NoPen if self.isChecked() else QPen(self._border, 1))
        painter.drawRoundedRect(track, radius, radius)

        inset = (self.height() - SWITCH_KNOB) / 2
        travel = track.width() - SWITCH_KNOB - 2 * inset
        x = inset + travel * self._offset
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(KNOB_SHADOW)
        painter.drawEllipse(QRectF(x, inset + 1, SWITCH_KNOB, SWITCH_KNOB))
        painter.setBrush(KNOB_COLOR)
        painter.drawEllipse(QRectF(x, inset, SWITCH_KNOB, SWITCH_KNOB))
