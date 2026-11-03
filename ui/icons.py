from pathlib import Path
from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QGuiApplication, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from ui.constants import ICONS_DIR, ICON_SIZE

__all__ = ["icon", "pixmap"]


def _dpr() -> float:
    screen = QGuiApplication.primaryScreen()
    return screen.devicePixelRatio() if screen is not None else 1.0


def icon(name: str, color: str, size: int = ICON_SIZE) -> QIcon:
    svg = (ICONS_DIR / f"{name}.svg").read_text(encoding="utf-8")
    renderer = QSvgRenderer(QByteArray(svg.replace("currentColor", color).encode("utf-8")))
    dpr = _dpr()
    image = QPixmap(round(size * dpr), round(size * dpr))
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    image.setDevicePixelRatio(dpr)
    return QIcon(image)


def pixmap(path: Path, width: int) -> QPixmap:
    dpr = _dpr()
    image = QPixmap(str(path)).scaledToWidth(round(width * dpr), Qt.TransformationMode.SmoothTransformation)
    image.setDevicePixelRatio(dpr)
    return image
    
