# --- ./ui/markdown.py ---


from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from PyQt6.QtGui import QTextDocument, QTextFrameFormat, QTextTable, QTextTableFormat
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.style import Style
from pygments.token import (
    Comment, Error, Keyword, Name, Number, Operator, Punctuation, String, Token
)
from pygments.util import ClassNotFound
from ui.constants import PLAIN, CODE_FONT, CODE_FONT_SIZE, TABLE_PADDING, TABLE_BORDER
from ui.style import THEMES, qcolor

__all__ = [
    "MD_FEATURES",
    "Part",
    "PartKind",
    "code_html",
    "split_markdown",
    "style_tables"
]

_FEATURE = QTextDocument.MarkdownFeature
MD_FEATURES = _FEATURE(_FEATURE.MarkdownDialectGitHub.value | _FEATURE.MarkdownNoHTML.value)
_FENCE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})[ \t]*([^\s`]*)[ \t]*$")
_TABLE_SEP = re.compile(r"^[ \t]{0,3}\|?[ \t]*:?-{1,}:?[ \t]*(\|[ \t]*:?-{1,}:?[ \t]*)+\|?[ \t]*$")
_SYNTAX = {
    Comment:            "italic #6E8FB5",
    Keyword:            "bold #6EC6E5",
    Keyword.Constant:   "bold #F0B429",
    Keyword.Type:       "#93D7EF",
    Name.Function:      "#93D7EF",
    Name.Class:         "bold #93D7EF",
    Name.Builtin:       "#8ED3B0",
    Name.Decorator:     "#FFB38A",
    String:             "#7FD6A3",
    String.Doc:         "italic #7FD6A3",
    Number:             "#F0B429",
    Operator:           "#9FC9E3",
    Punctuation:        "#9FC9E3",
    Error:              "#FF8A80",
}


class PartKind(Enum):
    TEXT = "text"
    CODE = "code"
    TABLE = "table"


@dataclass(frozen=True)
class Part:
    kind: PartKind
    content: str
    language: str = ""


def split_markdown(text: str) -> list[Part]:
    parts: list[Part] = []
    buffer: list[str] = []
    lines = text.split("\n")
    index = 0


    def flush() -> None:
        body = "\n".join(buffer).strip("\n")
        buffer.clear()
        if body.strip():
            parts.append(Part(PartKind.TEXT, body))

    while index < len(lines):
        line = lines[index]
        fence = _FENCE.match(line)
        if fence is not None:
            flush()
            index = _take_code(lines, index, fence, parts)
            continue
        if index + 1 < len(lines) and "|" in line and _TABLE_SEP.match(lines[index + 1]):
            flush()
            index = _take_table(lines, index, parts)
            continue
        buffer.append(line)
        index += 1
    flush()
    return parts


def _take_code(lines: list[str], start: int, fence: re.Match[str], parts: list[Part]) -> int:
    opening = fence.group(1)
    language = fence.group(2).lower()
    body: list[str] = []
    index = start + 1
    while index < len(lines):
        closing = _FENCE.match(lines[index])
        if closing is not None and _closes(opening, closing):
            index += 1
            break
        body.append(lines[index])
        index += 1
    parts.append(Part(PartKind.CODE, "\n".join(body), language))
    return index


def _closes(opening: str, closing: re.Match[str]) -> bool:
    mark = closing.group(1)
    return mark[0] == opening[0] and len(mark) >= len(opening) and not closing.group(2)


def _take_table(lines: list[str], start: int, parts: list[Part]) -> int:
    rows = [lines[start], lines[start + 1]]
    index = start + 2
    while index < len(lines) and lines[index].strip() and "|" in lines[index]:
        rows.append(lines[index])
        index += 1
    parts.append(Part(PartKind.TABLE, "\n".join(rows)))
    return index


@lru_cache(maxsize=4)
def _style(theme: str) -> type[Style]:
    tokens = THEMES[theme]

    class FukaiStyle(Style):
        background_color = tokens["code_bg"]
        styles = {
            Token: tokens["code_text"],
            Name: tokens["code_text"],
            Name.Attribute: tokens["code_text"],
            **_SYNTAX
        }

    return FukaiStyle


def code_html(code: str, language: str, theme: str) -> str:
    try:
        lexer = get_lexer_by_name(language or PLAIN)
    except ClassNotFound:
        lexer = get_lexer_by_name(PLAIN)
    formatter = HtmlFormatter(style=_style(theme), noclasses=True, nowrap=True)
    body = highlight(code, lexer, formatter).rstrip("\n")
    return (f'<pre style="font-family:{CODE_FONT}; font-size:{CODE_FONT_SIZE}px; margin:0; color:{THEMES[theme]["code_text"]};">{body}</pre>')


def style_tables(doc: QTextDocument, theme: str) -> None:
    tokens = THEMES[theme]
    for frame in doc.rootFrame().childFrames():
        if not isinstance(frame, QTextTable):
            continue
        table = QTextTableFormat()
        table.setBorder(TABLE_BORDER)
        table.setBorderStyle(QTextFrameFormat.BorderStyle.BorderStyle_Solid)
        table.setBorderBrush(qcolor(tokens["accent"]))
        table.setBorderCollapse(True)
        table.setCellPadding(TABLE_PADDING)
        table.setCellSpacing(0)
        table.setHeaderRowCount(1)
        frame.setFormat(table)
        for column in range(frame.columns()):
            cell = frame.cellAt(0, column)
            header = cell.format()
            header.setBackground(qcolor(tokens["chip"]))
            cell.setFormat(header)
