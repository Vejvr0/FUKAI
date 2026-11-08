import re
from string import Template
from PyQt6.QtGui import QColor
from ui.constants import CODE_FONT

__all__ = ["THEMES", "qcolor", "stylesheet"]

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
        "code_scroll": "rgba(205, 239, 251, 0.30)",
        "menu": "#F5FBFE", "shadow": "rgba(13, 30, 72, 0.20)",
        "ok": "#2ECC71", "warning": "#E0A100", "danger": "#C62828",
        "warn_bg": "rgba(240, 160, 40, 0.18)", "warn_text": "#8A5300",
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
        "code_scroll": "rgba(189, 232, 247, 0.26)",
        "menu": "#1F3760", "shadow": "rgba(0, 0, 0, 0.40)",
        "ok": "#2ECC71", "warning": "#F0B429", "danger": "#FF8A80",
        "warn_bg": "rgba(247, 201, 126, 0.14)", "warn_text": "#F7C97E",
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
    QListWidget#chatList::item { padding: 0; border: none; background: transparent; }

    QFrame#chatRow { border: 1px solid transparent; border-radius: 10px; background: transparent; }
    QFrame#chatRow:hover { background: $hover; }
    QFrame#chatRow[active="true"] { background: $side_glass; border-color: $side_glass_border; }
    QLabel#chatTitle { color: $side_text; }
    QLineEdit#chatEdit {
        background: $side_input;
        border: 1px solid $side_glass_border;
        border-radius: 7px;
        padding: 0 6px;
        color: $side_text;
        selection-background-color: $accent; selection-color: #0D1E48;
    }
    QToolButton#chatMore { border: none; border-radius: 7px; background: transparent; }
    QToolButton#chatMore:hover { background: $hover; }

    QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
    QScrollBar::handle:vertical { background: $chip_hover; border-radius: 4px; min-height: 24px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
    QScrollBar:horizontal { background: transparent; height: 8px; margin: 0; }
    QScrollBar::handle:horizontal { background: $chip_hover; border-radius: 4px; min-width: 24px; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
    
    QFrame#panel {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 $panel_top, stop:1 $panel_bottom);
        border: 1px solid $panel_border;
        border-radius: 22px;
    }
    QFrame#chatHeader, QFrame#settingsHeader, QFrame#propertiesHeader { background: transparent; border: none; border-bottom: 1px solid $line; }
    QFrame#propertiesFooter { background: transparent; border: none; border-top: 1px solid $line; }
    QLabel#headTitle  { font-size: 15px; font-weight: 600; }

    QFrame#hwChip { background: $chip; border: 1px solid $line; border-radius: 14px; }
    QFrame#hwChip:hover { background: $chip_hover; }
    QFrame#usagePanel { background: $chip; border: 1px solid $line; border-radius: 12px; }
    QLabel#usageText { color: $text_muted; font-size: 11px; }
    QLabel#hwText { color: $text_muted; font-size: 12px; }
    QLabel#hwDot  { background: $ok; border-radius: 4px; }
    QLabel#hwDot[backend="cpu"] { background: $warning; }

    QLabel#placeholder { color: $text_muted; font-size: 15px; }
    
    QLabel#welcomeText { font-size: 22px; font-weight: 600; }
    QScrollArea#messageList { background: transparent; border: none; }
    QFrame#bubble {
        background: $user_bubble;
        border-radius: 18px;
        border-bottom-right-radius: 6px;
    }
    QTextBrowser#bubbleText { background: transparent; border: none; color: $user_text; }
    QTextBrowser#answerText { background: transparent; border: none; color: $text; }
    QLabel#answerMeta { color: $text_muted; font-size: 12px; }

    QFrame#codeBlock { background: $code_bg; border: 1px solid $line; border-radius: 10px; }
    QFrame#codeHead  { background: transparent; border: none; border-bottom: 1px solid $code_scroll; }
    QLabel#codeLang  { color: $code_text; font-size: 12px; }
    QToolButton#codeCopy {
        color: $code_text; background: transparent; border: none;
        border-radius: 6px; padding: 3px 8px; font-size: 12px;
    }
    QToolButton#codeCopy:hover { background: $code_scroll; }
    QTextBrowser#codeBody  { background: transparent; border: none; color: $code_text; }
    QTextBrowser#tableBody { background: transparent; border: none; color: $text; }
    QFrame#codeBlock QScrollBar::handle:horizontal,
    QFrame#codeBlock QScrollBar::handle:vertical { background: $code_scroll; }

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
    QProgressBar#toastProgress        { border: none; background: $chip; border-radius: 2px; }
    QProgressBar#toastProgress::chunk { background: $accent; border-radius: 2px; }
    QWidget#composerColumn { background: transparent; }
    QFrame#composer {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 $glass_top, stop:1 $glass_bottom);
        border: 1px solid $glass_border;
        border-radius: 24px;
    }
    QFrame#composer[focused="true"] { border-color: $accent; }
    QPlainTextEdit#composerInput {
        background: transparent; border: none; padding: 0;
        color: $text; font-size: 15px;
        selection-background-color: $accent; selection-color: #0D1E48;
    }
    QLabel#composerHint { color: $text_muted; font-size: 12px; }
    QLabel#composerFoot { color: $text_muted; font-size: 11px; }

    QToolButton#roundButton, QToolButton#modelPill {
        background: $chip; border: none; border-radius: 18px; color: $text;
    }
    QToolButton#roundButton:hover, QToolButton#modelPill:hover { background: $chip_hover; }
    QToolButton#roundButton:disabled, QToolButton#modelPill:disabled { background: $chip; }
    QLabel#pillText { font-size: 14px; font-weight: 600; }
    QLabel#pillText:disabled { color: $text_muted; }

    QToolButton#send { background: $send; border: none; border-radius: 18px; }
    QToolButton#send:hover { background: $send_hover; }
    QToolButton#send:disabled { background: $chip; }

    QMenu#modelMenu, QMenu#chatMenu {
        background: $menu;
        border: 1px solid $glass_border;
        border-radius: 14px;
        padding: 6px;
        color: $text;
    }
    QMenu#modelMenu::item, QMenu#chatMenu::item { padding: 8px 10px; border-radius: 9px; color: $text; }
    QMenu#modelMenu::item:selected, QMenu#chatMenu::item:selected { background: $chip; }
    QMenu#modelMenu::item:disabled, QMenu#chatMenu::item:disabled { color: $text_muted; }
    QMenu#modelMenu::separator, QMenu#chatMenu::separator { height: 1px; background: $line; margin: 4px 6px; }
    QLabel#menuLabel {
        color: $text_muted; font-size: 11px; font-weight: 600;
        padding: 6px 10px 4px 10px;
    }
    QFrame#modelRow { border-radius: 9px; background: transparent; }
    QFrame#modelRow:hover { background: $chip; }
    QLabel#modelName { font-weight: 600; }
    QLabel#modelSub  { color: $text_muted; font-size: 12px; }
    QToolButton#modelTrash { border: none; border-radius: 7px; background: transparent; }
    QToolButton#modelTrash:hover { background: $chip_hover; }
    QLabel#modelEmpty { color: $text_muted; padding: 8px 10px; }

    QScrollArea#settingsBody { background: transparent; border: none; }
    QWidget#settingsWrap     { background: transparent; }

    QLabel#savedNote              { color: $text_muted; font-size: 12px; }
    QLabel#savedNote[flash="true"] { color: $accent_strong; font-weight: 600; }

    QLabel#groupLabel { color: $text_muted; font-size: 11px; font-weight: 600; }

    QFrame#card {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 $glass_top, stop:1 $glass_bottom);
        border: 1px solid $glass_border;
        border-radius: 18px;
    }
    QFrame#sep { background: $line; border: none; min-height: 1px; max-height: 1px; }

    QLabel#setIcon  { background: $chip; border-radius: 12px; }
    QLabel#setTitle { font-size: 15px; font-weight: 600; }
    QLabel#setDesc  { color: $text_muted; font-size: 12px; }

    QLineEdit#pathField {
        background: $chip;
        border: 1px solid $line;
        border-radius: 10px;
        padding: 0 12px;
        color: $text;
        font-family: $code_font; font-size: 13px;
        selection-background-color: $accent; selection-color: #0D1E48;
    }
    QPushButton#folderBtn {
        background: $send; color: $send_text;
        border: none; border-radius: 10px;
        padding: 0 16px;
        font-weight: 600;
    }
    QPushButton#folderBtn:hover { background: $send_hover; }

    QLabel#foundHead { color: $text_muted; font-size: 12px; font-weight: 600; }
    QFrame#foundItem { background: transparent; border-radius: 9px; }
    QFrame#foundItem:hover { background: $chip; }
    QLabel#fName { font-size: 13px; }
    QLabel#fMeta { color: $text_muted; font-size: 12px; }
    QLabel#foundEmpty {
        color: $text_muted; font-size: 13px;
        border: 1px dashed $line; border-radius: 10px;
        padding: 12px;
    }
    QLabel#pageFoot { color: $text_muted; font-size: 11px; }

    QScrollArea#propertiesBody { background: transparent; border: none; }
    QFrame#scopeChip { background: $chip; border: 1px solid $line; border-radius: 14px; }
    QLabel#scopeText { color: $text_muted; font-size: 12px; }
    QLabel#modeLabel { font-size: 13px; font-weight: 600; }

    QLabel#badge { border-radius: 10px; padding: 2px 8px; font-size: 11px; font-weight: 600; }
    QLabel#badge[kind="reload"] { background: $warn_bg; color: $warn_text; }
    QLabel#badge[kind="live"]   { background: $chip; color: $accent_strong; }

    QLabel#pLabel { font-size: 15px; font-weight: 600; }
    QLabel#pKey {
        background: $chip; border-radius: 6px; padding: 1px 6px;
        color: $text_muted; font-family: $code_font; font-size: 11px;
    }
    QLabel#pHint { color: $text_muted; font-size: 12px; }
    QLabel#pDesc { color: $text_muted; font-size: 12px; }
    QLabel#pTag  { color: $accent_strong; font-size: 12px; font-weight: 600; }
    QLabel#pNote {
        background: $warn_bg; color: $warn_text;
        border-radius: 10px; padding: 8px 12px; font-size: 12px;
    }

    QPlainTextEdit#promptBox {
        background: $chip;
        border: 1px solid $line;
        border-radius: 12px;
        padding: 8px 10px;
        color: $text; font-size: 14px;
        selection-background-color: $accent; selection-color: #0D1E48;
    }
    QPlainTextEdit#promptBox:focus { border-color: $accent; }
    QPushButton#preset {
        background: $glass; border: 1px solid $glass_border; border-radius: 14px;
        padding: 0 12px; font-size: 12px; color: $text;
    }
    QPushButton#preset:hover { background: $chip_hover; }

    QLabel#applyStatus { color: $text_muted; font-size: 12px; }
    QLabel#applyStatus[state="dirty"] { color: $warn_text; font-weight: 600; }
    QLabel#applyStatus[state="ok"]    { color: $accent_strong; font-weight: 600; }
    QPushButton#ghostBtn {
        background: $chip; border: none; border-radius: 10px;
        padding: 0 16px; font-weight: 600; color: $text;
    }
    QPushButton#ghostBtn:hover { background: $chip_hover; }
    QPushButton#applyBtn {
        background: $send; color: $send_text; border: none; border-radius: 10px;
        padding: 0 16px; font-weight: 600;
    }
    QPushButton#applyBtn:hover { background: $send_hover; }
    QPushButton#applyBtn:disabled { background: $chip; color: $text_muted; }

    QSpinBox#num, QDoubleSpinBox#num {
        background: $chip;
        border: 1px solid $line;
        border-radius: 8px;
        padding: 0 8px;
        color: $text;
        font-family: $code_font; font-size: 12px;
        selection-background-color: $accent; selection-color: #0D1E48;
    }
    QSpinBox#num:focus, QDoubleSpinBox#num:focus { border-color: $accent; }
    QSpinBox#num:disabled, QDoubleSpinBox#num:disabled { color: $text_muted; }

    QSlider::groove:horizontal { height: 6px; background: $chip_hover; border-radius: 3px; }
    QSlider::sub-page:horizontal { background: $accent; border-radius: 3px; }
    QSlider::add-page:horizontal { background: $chip_hover; border-radius: 3px; }
    QSlider::handle:horizontal {
        width: 12px; height: 12px;
        margin: -5px 0;
        border-radius: 8px;
        background: #FFFFFF;
        border: 2px solid $accent_strong;
    }
    QSlider::handle:horizontal:disabled { border-color: $text_muted; }

    QLabel#tick { color: $text_muted; font-family: $code_font; font-size: 11px; }
    QLabel#tick[on="true"] { color: $accent_strong; font-weight: 700; }
    QLabel#pMemory { color: $text_muted; font-size: 12px; }
    QLabel#pMin, QLabel#pMax {
        color: $text_muted; font-family: $code_font; font-size: 11px; min-width: 34px;
    }
    QLabel#miniLabel { color: $text_muted; font-size: 12px; }
    QLineEdit#num {
        background: $chip;
        border: 1px solid $line;
        border-radius: 8px;
        padding: 0 8px;
        color: $text;
        font-family: $code_font; font-size: 12px;
        selection-background-color: $accent; selection-color: #0D1E48;
    }
    QLineEdit#num:focus { border-color: $accent; }
    QLineEdit#num:disabled { color: $text_muted; }
    QLabel#easyHint {
        color: $text_muted; font-size: 13px;
        border: 1px dashed $line; border-radius: 14px;
        padding: 12px 16px;
    }
""")

_RGBA = re.compile(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)")


def qcolor(value: str) -> QColor:
    match = _RGBA.fullmatch(value.strip())
    if match is None:
        return QColor(value)
    r, g, b, a = match.groups()
    return QColor(int(r), int(g), int(b), round(float(a) * 255))


def stylesheet(theme: str) -> str:
    return _QSS.substitute(THEMES[theme], code_font=CODE_FONT)