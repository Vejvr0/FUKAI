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
    
    
    def __init__(self, notice: Notice, parent: QWidget, *, persistent: bool = False, progress: bool = False) -> None:
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
        self._hint: QLabel | None = None
        if notice.hint:
            self._hint = self._label(notice.hint, "toastHint")
            layout.addWidget(self._hint)
            
        self._progress: QProgressBar | None = None
        if progress:
            persistent = True
            self._progress = QProgressBar()
            self._progress.setObjectName("toastProgress")
            self._progress.setTextVisible(False)
            self._progress.setFixedHeight(4)
            self._progress.setRange(0, TOAST_TIMELINE_STEPS)
            self._progress.setValue(0)
            layout.addSpacing(6)
            layout.addWidget(self._progress)
            
        self._timeline: QTimeLine | None = None
        duration = 0 if persistent else DURATIONS[notice.severity]     # 0 = bez časovej osi, zavrie ho volajúci
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
    
    
    def set_progress(self, fraction: float, text: str | None = None) -> None:
        if self._progress is not None:
            self._progress.setValue(round(max(0.0, min(1.0, fraction)) * TOAST_TIMELINE_STEPS))
        if text is not None and self._hint is not None:
            self._hint.setText(text)
    
    
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
    
    
    def show_notice(self, notice: Notice, *, persistent: bool = False, progress: bool = False) -> Toast:
        toast = Toast(notice, self._window, persistent=persistent, progress=progress)
        toast.closed.connect(self._remove)
        self._toasts.append(toast)
        toast.show()
        toast.raise_()
        self._relayout()
        toast.start()
        return toast
    
    
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