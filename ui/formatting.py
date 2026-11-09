from __future__ import annotations
from ui.constants import TOKENS_PER_PAGE

__all__ = [
    "answer_meta",
    "approx_tokens",
    "int_text",
    "model_subtitle",
    "pages_text",
    "short_tokens",
    "size_text",
    "sources_text",
    "tokens_text"
]


def size_text(size_mb: float) -> str:
    if size_mb >= 1024:
        return f"{size_mb / 1024:.1f} GB".replace(".", ",")
    return f"{size_mb:.0f} MB"


def model_subtitle(model: dict) -> str:
    if model.get("size_mb") is None:
        return "súbor chýba"
    meta = model.get("meta") or {}
    parts = [meta.get("quant"), meta.get("size_label"), size_text(model["size_mb"])]
    return " · ".join(p for p in parts if p)


def answer_meta(data: dict) -> str:
    stats = data.get("stats") or {}
    parts = [data.get("model")]
    if stats.get("tokens_per_s"):
        parts.append(f"{stats['tokens_per_s']:.0f} tok/s")
    if stats.get("total_s") is not None:
        parts.append(f"{stats['total_s']:.1f} s".replace(".", ","))
    sources = (data.get("web") or {}).get("sources")
    if sources:
        parts.append(sources_text(len(sources)))
    if data.get("finish_reason") == "length":
        parts.append("skrátená - dosiahnutý limit tokenov")
    return " · ".join(p for p in parts if p)


def sources_text(count: int) -> str:
    word = "zdroj" if count == 1 else "zdroje" if count < 5 else "zdrojov"
    return f"{count} {word}"


def tokens_text(count: int) -> str:
    if count <= 0:
        return "tokeny sa dopočítajú"
    word = "token" if count == 1 else "tokeny" if count < 5 else "tokenov"
    return f"~{count:,} {word}".replace(",", " ")


def int_text(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def short_tokens(value: int) -> str:
    return f"{value // 1024}K" if value >= 1024 and value % 1024 == 0 else str(value)


def pages_text(n_ctx: int) -> str:
    pages = max(1, round(n_ctx / TOKENS_PER_PAGE))
    word = "strana" if pages == 1 else "strany" if pages < 5 else "strán"
    return f"{int_text(pages)} {word}"


def approx_tokens(text: str) -> int:
    return max(1, round(len(text) / 4))
