from string import Template

__all__ = ["THEMES", "stylesheet"]

THEMES: dict[str, dict[str, str]] = {
    "light": {
        "window": "#2A368B",
        "sidebar_top": "#4791C0", "sidebar_bottom": "#3D87B6",
        "side_border": "rgba(13, 30, 72, 0.25)",
        "side_text": "#0D1E48", "side_muted": "rgba(13, 30, 72, 0.62)",
        "side_glass": "rgba(255, 255, 255, 0.28)",
        "side_glass_border": "rgba(255, 255, 255, 0.50)",
        "side_input": "rgba(255, 255, 255, 0.80)",
        "hover": "rgba(255, 255, 255, 0.20)",
        "tab_active_top": "#93D7EF", "tab_active_bottom": "#6EC6E5",
        "tab_active_border": "#0D1E48",
        "panel_top": "#B9E6F6", "panel_bottom": "#9AD7EE",
        "panel_border": "rgba(255, 255, 255, 0.65)",
        "text": "#0D1E48", "text_muted": "rgba(13, 30, 72, 0.58)",
        "line": "rgba(13, 30, 72, 0.12)",
        "glass_top": "rgba(255, 255, 255, 0.80)", "glass_bottom": "rgba(255, 255, 255, 0.55)",
        "glass_border": "rgba(255, 255, 255, 0.95)", "glass": "rgba(255, 255, 255, 0.55)",
        "chip": "rgba(13, 30, 72, 0.07)", "chip_hover": "rgba(13, 30, 72, 0.13)",
        "accent": "#6EC6E5", "accent_strong": "#2A368B",
        "user_bubble": "#2A368B", "user_text": "#FFFFFF",
        "send": "#2A368B", "send_hover": "#3644A3", "send_text": "#FFFFFF",
        "code_bg": "#0D1E48", "code_text": "#CDEFFB",
        "menu": "#F5FBFE", "shadow": "rgba(13, 30, 72, 0.20)",
        "ok": "#2ECC71", "warning": "#E0A100", "danger": "#C62828",
    },
    "dark": {
        "window": "#0D1E48",
        "sidebar_top": "#2D4C78", "sidebar_bottom": "#29466F",
        "side_border": "rgba(110, 198, 229, 0.15)",
        "side_text": "#E4F3FB", "side_muted": "rgba(228, 243, 251, 0.55)",
        "side_glass": "rgba(255, 255, 255, 0.08)",
        "side_glass_border": "rgba(255, 255, 255, 0.14)",
        "side_input": "rgba(13, 30, 72, 0.60)",
        "hover": "rgba(255, 255, 255, 0.07)",
        "tab_active_top": "rgba(110, 198, 229, 0.32)", "tab_active_bottom": "rgba(110, 198, 229, 0.18)",
        "tab_active_border": "rgba(110, 198, 229, 0.60)",
        "panel_top": "#1B325C", "panel_bottom": "#14284F",
        "panel_border": "rgba(110, 198, 229, 0.16)",
        "text": "#E4F3FB", "text_muted": "rgba(228, 243, 251, 0.52)",
        "line": "rgba(255, 255, 255, 0.08)",
        "glass_top": "rgba(255, 255, 255, 0.10)", "glass_bottom": "rgba(255, 255, 255, 0.05)",
        "glass_border": "rgba(255, 255, 255, 0.14)", "glass": "rgba(255, 255, 255, 0.06)",
        "chip": "rgba(255, 255, 255, 0.08)", "chip_hover": "rgba(255, 255, 255, 0.14)",
        "accent": "#6EC6E5", "accent_strong": "#6EC6E5",
        "user_bubble": "#3D87B6", "user_text": "#FFFFFF",
        "send": "#6EC6E5", "send_hover": "#8AD3EC", "send_text": "#0D1E48",
        "code_bg": "#0A1736", "code_text": "#BDE8F7",
        "menu": "#1F3760", "shadow": "rgba(0, 0, 0, 0.40)",
        "ok": "#2ECC71", "warning": "#F0B429", "danger": "#FF8A80",
    },
}

_QSS = Template("""
    QWidget { font-size: 14px; }
    QLabel  { color: $text; background: transparent; }
    
    QWidget#central { background: $window; }

    QFrame#sidebar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 $sidebar_top, stop:1 $sidebar_bottom);
        border: none;
        border-right: 1px solid $side_border;
    }

    QPushButton#tab {
        min-height: 38px; max-height: 38px;
        padding: 0 14px;
        border: 1px solid transparent;
        border-radius: 12px;
        background: transparent;
        color: $side_text;
        font-size: 15px;
        text-align: left;
    }
    QPushButton#tab:hover { background: $hover; }
    QPushButton#tab:checked {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 $tab_active_top, stop:1 $tab_active_bottom);
        border-color: $tab_active_border;
        font-weight: 600;
    }

    QPushButton#newChat {
        min-height: 36px; max-height: 36px;
        padding: 0 14px;
        border: 1px solid $side_glass_border;
        border-radius: 12px;
        background: $side_glass;
        color: $side_text;
        font-weight: 600;
        text-align: left;
    }
    QPushButton#newChat:hover { background: $hover; }

    QLabel#listLabel { color: $side_muted; font-size: 12px; font-weight: 600; padding: 12px 12px 4px 12px; }

    QListWidget#chatList { background: transparent; border: none; outline: 0; color: $side_text; }
    QListWidget#chatList::item {
        padding: 0 8px;
        border: 1px solid transparent;
        border-radius: 10px;
        color: $side_text;
    }
    QListWidget#chatList::item:hover    { background: $hover; }
    QListWidget#chatList::item:selected { background: $side_glass; border-color: $side_glass_border; }

    QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
    QScrollBar::handle:vertical { background: $chip_hover; border-radius: 4px; min-height: 24px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
    
    QFrame#panel {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 $panel_top, stop:1 $panel_bottom);
        border: 1px solid $panel_border;
        border-radius: 22px;
    }
    QFrame#chatHeader { background: transparent; border: none; border-bottom: 1px solid $line; }
    QLabel#headTitle  { font-size: 15px; font-weight: 600; }

    QFrame#hwChip { background: $chip; border: 1px solid $line; border-radius: 14px; }
    QLabel#hwText { color: $text_muted; font-size: 12px; }
    QLabel#hwDot  { background: $ok; border-radius: 4px; }
    QLabel#hwDot[backend="cpu"] { background: $warning; }

    QLabel#placeholder { color: $text_muted; font-size: 15px; }

    QFrame#toast {
        background: $menu;
        border: 1px solid $line;
        border-left: 3px solid $accent;
        border-radius: 8px;
    }
    QFrame#toast[severity="warning"] { border-left-color: $warning; }
    QFrame#toast[severity="error"]   { border-left-color: $danger; }

    QLabel#toastTitle   { font-size: 13px; font-weight: 600; }
    QLabel#toastMessage { font-size: 13px; }
    QLabel#toastHint    { font-size: 12px; color: $text_muted; }

    QPushButton#toastClose       { border: none; background: transparent; color: $text_muted; font-size: 12px; padding: 0; }
    QPushButton#toastClose:hover { color: $text; }

    QProgressBar#toastTimeline        { border: none; background: $chip; border-radius: 1px; }
    QProgressBar#toastTimeline::chunk { background: $accent; border-radius: 1px; }
    QFrame#toast[severity="warning"] QProgressBar#toastTimeline::chunk { background: $warning; }
""")

def stylesheet(theme: str) -> str:
    return _QSS.substitute(THEMES[theme])