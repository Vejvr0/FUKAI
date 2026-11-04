from pathlib import Path
from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QGuiApplication, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from ui.constants import ICONS_DIR, ICON_SIZE, ICON_DISABLED_OPACITY

__all__ = ["icon", "pixmap"]


def _dpr() -> float:
    screen = QGuiApplication.primaryScreen()
    return screen.devicePixelRatio() if screen is not None else 1.0


def _render(name: str, color: str, size: int, opacity: float = 1.0) -> QPixmap:
    svg = (ICONS_DIR / f"{name}.svg").read_text(encoding="utf-8")
    renderer = QSvgRenderer(QByteArray(svg.replace("currentColor", color).encode("utf-8")))
    dpr = _dpr()
    image = QPixmap(round(size * dpr), round(size * dpr))
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setOpacity(opacity)
    renderer.render(painter)
    painter.end()
    image.setDevicePixelRatio(dpr)
    return image


def icon(name: str, color: str, size: int = ICON_SIZE, *, disabled_color: str | None = None) -> QIcon:
    result = QIcon(_render(name, color, size))
    result.addPixmap(_render(name, disabled_color or color, size, ICON_DISABLED_OPACITY), QIcon.Mode.Disabled)
    return result


def pixmap(path: Path, width: int) -> QPixmap:
    dpr = _dpr()
    image = QPixmap(str(path)).scaledToWidth(round(width * dpr), Qt.TransformationMode.SmoothTransformation)
    image.setDevicePixelRatio(dpr)
    return image
