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
        table.setBorderBrush(qcolor(tokens["accent"]))     # qcolor: token môže byť rgba(...)
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


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    from PyQt6.QtWidgets import QApplication

    app = QApplication([])
    failed = 0

    def check(label: str, passed: bool, detail: str = "") -> None:
        global failed
        failed += 0 if passed else 1
        print(f"  {'OK  ' if passed else 'CHYBA'} {label}" + (f"   {detail}" if detail else ""))

    def kinds(text: str) -> str:
        return " ".join(part.kind.value for part in split_markdown(text))

    print("--- delenie na casti ---")
    check("cisty text", kinds("len veta") == "text", kinds("len veta"))
    check("text + kod + text",
          kinds("pred\n\n```python\nx = 1\n```\n\npo") == "text code text")
    check("kod bez jazyka", split_markdown("```\nx = 1\n```")[0].language == "")
    check("jazyk sa normalizuje na male", split_markdown("```PYTHON\nx\n```")[0].language == "python")
    check("vlnovkovy fence", kinds("~~~js\nlet a = 1;\n~~~") == "code")
    check("tri apostrofy vnutri dlhsieho fence",
          split_markdown("````\n```\nx\n````")[0].content == "```\nx")
    check("neuzavrety fence je stale kod",
          kinds("text\n\n```python\nx = 1\ny = 2") == "text code",
          repr(split_markdown("text\n\n```python\nx = 1\ny = 2")[1].content))
    check("tabulka na konci", kinds("pred\n\n| a | b |\n|---|---|\n| 1 | 2 |") == "text table")
    check("tabulka hned na zaciatku", kinds("| a | b |\n|---|---|\n| 1 | 2 |") == "table")
    check("zvislice bez oddelovaca nie su tabulka", kinds("a | b\nc | d") == "text")
    check("prazdny vstup", split_markdown("") == [])
    check("samy biely znak", split_markdown("\n\n   \n") == [])

    print("\n--- rozdelenie realnej odpovede ---")
    answer = ("Postup:\n\n1. prvy\n2. druhy\n\n```python\ndef f(x):\n    return x\n```\n\n"
              "Tabulka:\n\n| Model | tok/s |\n|---|---:|\n| Gemma | 107 |\n\nKoniec.")
    for part in split_markdown(answer):
        head = part.content.split("\n")[0][:40]
        print(f"  {part.kind.value:5} {part.language or '-':8} {len(part.content):4} znakov | {head}")

    print("\n--- zvyraznenie kodu ---")
    html = code_html("def f(x):\n    return x  # pozn\n", "python", "light")
    check("obsahuje explicitnu farbu textu", "color:#CDEFFB" in html.replace(" ", ""))
    check("obsahuje farbu klucoveho slova", "#6EC6E5" in html)
    check("nekonci prazdnym riadkom", not html.endswith("\n</pre>"))
    check("neznamy jazyk nespadne", "<pre" in code_html("x", "gibberish", "dark"))
    check("prazdny jazyk nespadne", "<pre" in code_html("x", "", "dark"))
    check("prazdny kod nespadne", "<pre" in code_html("", "python", "light"))
    check("styl sa cachuje", _style("light") is _style("light"))
    print(f"  dlzka HTML pre 2 riadky: {len(html)} znakov")

    print("\n--- styl tabulky ---")
    doc = QTextDocument()
    doc.setMarkdown("| Model | tok/s |\n|---|---:|\n| Gemma | 107 |\n", MD_FEATURES)
    style_tables(doc, "light")
    table = next(f for f in doc.rootFrame().childFrames() if isinstance(f, QTextTable))
    fmt = table.format()
    background = table.cellAt(0, 0).format().background().color()
    check("ram je nastaveny", fmt.border() == TABLE_BORDER, f"border={fmt.border()}")
    check("hlavickovy riadok", fmt.headerRowCount() == 1)
    check("odsadenie buniek", fmt.cellPadding() == TABLE_PADDING)
    check("hlavicka ma pozadie", background.isValid() and background.alpha() > 0,
          f"{background.name()} alpha={background.alpha()}")
    print(f"  tabulka {table.rows()}x{table.columns()}")

    print("\n--- surove HTML sa neinterpretuje ---")
    doc = QTextDocument()
    doc.setMarkdown('Text <b>html</b> a <img src="http://x/y.png"> koniec. Porovnanie a<b.',
                    MD_FEATURES)
    text = doc.toPlainText()
    check("text zostal cely", text.endswith("Porovnanie a<b."), repr(text))

    print(f"\nVYSLEDOK: {'vsetko OK' if not failed else f'{failed} chyb'}")
    sys.exit(1 if failed else 0)
