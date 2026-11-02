from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
SPLASH_IMAGE = ASSETS_DIR / "splash_screen.png"
ICO = ASSETS_DIR / "ico" / "fukai.ico"
ICNS = ASSETS_DIR / "icns" / "fukai.icns"
LOGO = ASSETS_DIR / "logo.png"
LOGO_TRANSPARENT = ASSETS_DIR / "logo_transparent.png"
SPLASH_WIDTH = 800
SPLASH_TIME = 2000
SPLASH_BAR_TOP = 1266 / 1320
SPLASH_BAR_BOTTOM = 1316 / 1320
SPLASH_TEXT_LEFT = 0.30
SPLASH_TEXT_MARGIN = 12
SPLASH_TEXT_COLOR = "#ffffff"
WINDOW_SIZE = (1100, 720)
WINDOW_MIN_SIZE = (800, 560)
WINDOWS_APP_ID = "FEIT.FUKAI"
