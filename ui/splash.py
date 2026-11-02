from __future__ import annotations
from PyQt6.QtWidgets import QSplashScreen
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QGuiApplication, QColor, QPainter, QPixmap
from ui.constants import (
    SPLASH_IMAGE, SPLASH_WIDTH, SPLASH_BAR_TOP, SPLASH_BAR_BOTTOM,
    SPLASH_TEXT_LEFT, SPLASH_TEXT_MARGIN, SPLASH_TEXT_COLOR
)

__all__ = ["SplashScreen"]


def _load_pixmap() -> QPixmap:
    source = QPixmap(str(SPLASH_IMAGE))
    if source.isNull():
        source = QPixmap(SPLASH_WIDTH, SPLASH_WIDTH * 13 // 16)
        source.fill(QColor("#3d87b6"))
    screen = QGuiApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0
    pixmap = source.scaledToWidth(round(SPLASH_WIDTH * dpr), Qt.TransformationMode.SmoothTransformation)
    pixmap.setDevicePixelRatio(dpr)
    return pixmap


class SplashScreen(QSplashScreen):
    def __init__(self) -> None:
        super().__init__(_load_pixmap(), Qt.WindowType.WindowStaysOnTopHint)
        
    
    def drawContents(self, painter: QPainter) -> None:
        w, h = self.width(), self.height()
        bar = QRectF(w * SPLASH_TEXT_LEFT, h * SPLASH_BAR_TOP, w * (1 - SPLASH_TEXT_LEFT) - SPLASH_TEXT_MARGIN, h * (SPLASH_BAR_BOTTOM - SPLASH_BAR_TOP))
        font = painter.font()
        font.setPixelSize(max(10, round(bar.height() * 0.5)))
        painter.setFont(font)
        painter.setPen(QColor(SPLASH_TEXT_COLOR))
        text = painter.fontMetrics().elidedText(
            self.message(), Qt.TextElideMode.ElideLeft, round(bar.width())
        )
        painter.drawText(bar, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, text)
    
    
    def mousePressEvent(self, event) -> None:
        pass
    
        