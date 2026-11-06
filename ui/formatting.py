from __future__ import annotations

__all__ = ["answer_meta", "size_text"]


def size_text(size_mb: float) -> str:
    if size_mb >= 1024:
        return f"{size_mb / 1024:.1f} GB".replace(".", ",")
    return f"{size_mb:.0f} MB"


def answer_meta(data: dict) -> str:
    stats = data.get("stats") or {}
    parts = [data.get("model")]
    if stats.get("tokens_per_s"):
        parts.append(f"{stats['tokens_per_s']:.0f} tok/s")
    if stats.get("total_s") is not None:
        parts.append(f"{stats['total_s']:.1f} s".replace(".", ","))
    if data.get("finish_reason") == "length":
        parts.append("skrátená - dosiahnutý limit tokenov")
    return " · ".join(p for p in parts if p)
