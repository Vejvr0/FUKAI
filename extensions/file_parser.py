from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from core.constants import (
    ATTACHMENT_MAX_MB, ATTACHMENT_MAX_ROWS, BINARY_PROBE_BYTES, DOCX_SUFFIX, PDF_SUFFIX,
    TEXT_ENCODINGS, TEXT_SUFFIXES, XLSX_SUFFIX
)
from core.errors import AttachmentError, AttachmentParseError, AttachmentTooLargeError, UnsupportedAttachmentError

__all__ = [
    "Attachment",
    "extract",
    "supported"
]


@dataclass(frozen=True)
class Attachment:
    title: str
    text: str
    trimmed: bool = False      # orezaná na rozpočet kontextu pri pripnutí (§2)

    @property
    def chars(self) -> int:
        return len(self.text)


def supported(path: str | Path) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in TEXT_SUFFIXES or suffix in (PDF_SUFFIX, XLSX_SUFFIX, DOCX_SUFFIX)


def extract(path: str | Path) -> Attachment:
    path = Path(path)
    suffix = path.suffix.lower()
    if not supported(path):
        raise UnsupportedAttachmentError(f"prípona {suffix!r}: {path}")

    try:
        size_mb = path.stat().st_size / (1024 * 1024)
    except OSError as exc:
        raise AttachmentError(
            f"{type(exc).__name__}: {exc}",
            message="Súbor sa nepodarilo otvoriť."
        ) from exc

    if size_mb > ATTACHMENT_MAX_MB:
        raise AttachmentTooLargeError(
            f"{size_mb:.0f} MB, limit {ATTACHMENT_MAX_MB} MB: {path}",
            hint=f"Najväčšia príloha môže mať veľkosť maximálne {ATTACHMENT_MAX_MB} MB. Rozdel súbor na menšie časti."
        )

    readers = {PDF_SUFFIX: _read_pdf, XLSX_SUFFIX: _read_xlsx, DOCX_SUFFIX: _read_docx}
    reader = readers.get(suffix, _read_text)
    try:
        text = reader(path)
    except AttachmentError:
        raise
    except Exception as exc:
        raise AttachmentParseError(f"{type(exc).__name__}: {exc} ({path})") from exc
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise AttachmentParseError(f"prázdny výstup: {path}")
    return Attachment(title=path.name, text=text)


def _read_text(path: Path) -> str:
    data = path.read_bytes()
    if b"\x00" in data[:BINARY_PROBE_BYTES]:
        raise AttachmentParseError(f"binárny obsah: {path}")
    for encoding in TEXT_ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise AttachmentParseError(f"neznáme kódovanie: {path}")


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(path)
    if reader.is_encrypted and not reader.decrypt(""):
        raise AttachmentParseError(
            f"PDF je zašifrované: {path}",
            message="PDF je chránené heslom",
            hint="Odomkni súbor a pridaj ho znova."
        )
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(page.strip() for page in pages if page.strip())
    if not text:
        raise AttachmentParseError(
            f"žiadny textový obsah, {len(pages)} strán: {path}",
            message="PDF neobsahuje text, iba obrázky.",
            hint="Vyzerá to na sken. FUKAI text z obrázkov nečíta (OCR nie je podporované)."
        )
    return text


def _read_xlsx(path: Path) -> str:
    from openpyxl import load_workbook

    book = load_workbook(path, read_only=True, data_only=True)
    try:
        parts = []
        for sheet in book.worksheets:
            table = _sheet_table(sheet)
            if table:
                parts.append(f"## {sheet.title}\n\n{table}")
        return "\n\n".join(parts)
    finally:
        book.close()


def _sheet_table(sheet) -> str:
    rows = []
    cut = False
    for index, row in enumerate(sheet.iter_rows(values_only=True)):
        if index >= ATTACHMENT_MAX_ROWS:
            cut = True
            break
        if any(cell is not None for cell in row):
            rows.append([_cell(cell) for cell in row])
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    lines = ["| " + " | ".join(row + [""] * (width - len(row))) + " |" for row in rows]
    lines.insert(1, "|" + "---|" * width)
    if cut:
        lines.append(f"\n*(zobrazených prvých {ATTACHMENT_MAX_ROWS} riadkov)*")
    return "\n".join(lines)


def _cell(value) -> str:
    return "" if value is None else str(value).replace("|", "\\|").replace("\n", " ").strip()


def _read_docx(path: Path) -> str:
    from docx import Document
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = Document(str(path))
    parts = []
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            text = Paragraph(child, document).text.strip()
            if text:
                parts.append(text)
        elif child.tag == qn("w:tbl"):
            table = _docx_table(Table(child, document))
            if table:
                parts.append(table)
    return "\n\n".join(parts)


def _docx_table(table) -> str:
    rows = [[_cell(cell.text) for cell in row.cells] for row in table.rows[:ATTACHMENT_MAX_ROWS]]
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    lines = ["| " + " | ".join(row + [""] * (width - len(row))) + " |" for row in rows]
    lines.insert(1, "|" + "---|" * width)
    return "\n".join(lines)
