from __future__ import annotations
from PyQt6.QtCore import QEasingCurve, QEvent, QObject, Qt, QTimeLine, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)
from core.errors import Notice, Severity
from ui.constants import TOAST_WIDTH, TOAST_TOP, TOAST_RIGHT, TOAST_SPACING, TOAST_TIMELINE_STEPS

__all__ = ["Toast", "ToastHost"]

TITLES = {
    Severity.INFO: "Informácia",
    Severity.WARNING: "Varovanie",
    Severity.ERROR: "Chyba"
}
DURATIONS = {
    Severity.INFO: 3000,
    Severity.WARNING: 5000,
    Severity.ERROR: 0
}


class Toast(QFrame):
    closed = pyqtSignal(object)
    
    
    def __init__(self, notice: Notice, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setProperty("severity", notice.severity.value)
        self.setFixedWidth(TOAST_WIDTH)
        self._closing = False
        
        title = QLabel(TITLES[notice.severity])
        title.setObjectName("toastTitle")
        close = QPushButton("×")
        close.setObjectName("toastClose")
        close.setFixedSize(16, 16)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(self.dismiss)
        
        header = QHBoxLayout()
        header.addWidget(title, 1)
        header.addWidget(close)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(2)
        layout.addLayout(header)
        layout.addWidget(self._label(notice.message, "toastMessage"))
        if notice.hint:
            layout.addWidget(self._label(notice.hint, "toastHint"))
            
        self._timeline: QTimeLine | None = None
        duration = DURATIONS[notice.severity]
        if duration:
            bar = QProgressBar()
            bar.setObjectName("toastTimeline")
            bar.setTextVisible(False)
            bar.setFixedHeight(2)
            bar.setRange(0, TOAST_TIMELINE_STEPS)
            bar.setValue(TOAST_TIMELINE_STEPS)
            layout.addSpacing(6)
            layout.addWidget(bar)
            
            self._timeline = QTimeLine(duration, self)
            self._timeline.setFrameRange(TOAST_TIMELINE_STEPS, 0)
            self._timeline.setEasingCurve(QEasingCurve(QEasingCurve.Type.Linear))
            self._timeline.frameChanged.connect(bar.setValue)
            self._timeline.finished.connect(self.dismiss)

        self.setFixedHeight(self.heightForWidth(TOAST_WIDTH))
    
    
    @staticmethod
    def _label(text: str, name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(name)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label
    
    
    def start(self) -> None:
        if self._timeline is not None:
            self._timeline.start()
    
    
    def dismiss(self) -> None:
        if self._closing:
            return
        self._closing = True
        if self._timeline is not None:
            self._timeline.stop()
        self.hide()
        self.closed.emit(self)
        self.deleteLater()
    
    
    def enterEvent(self, event) -> None:
        if self._timeline is not None and self._timeline.state() == QTimeLine.State.Running:
            self._timeline.setPaused(True)
        super().enterEvent(event)
    
    
    def leaveEvent(self, event) -> None:
        if self._timeline is not None and self._timeline.state() == QTimeLine.State.Paused:
            self._timeline.setPaused(False)
        super().leaveEvent(event)
    
    
class ToastHost(QObject):
    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        self._window = window
        self._toasts: list[Toast] = []
        window.installEventFilter(self)
    
    
    def show_notice(self, notice: Notice) -> None:
        toast = Toast(notice, self._window)
        toast.closed.connect(self._remove)
        self._toasts.append(toast)
        toast.show()
        toast.raise_()
        self._relayout()
        toast.start()
    
    
    def _remove(self, toast: Toast) -> None:
        self._toasts.remove(toast)
        self._relayout()
    
    
    def _relayout(self) -> None:
        x = self._window.width() - TOAST_WIDTH - TOAST_RIGHT
        y = TOAST_TOP
        for toast in self._toasts:
            toast.move(x, y)
            y += toast.height() + TOAST_SPACING
    
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._window and event.type() == QEvent.Type.Resize:
            self._relayout()
        return False