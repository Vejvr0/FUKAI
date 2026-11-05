from __future__ import annotations

__all__ = ["size_text"]


def size_text(size_mb: float) -> str:
    if size_mb >= 1024:
        return f"{size_mb / 1024:.1f} GB".replace(".", ",")
    return f"{size_mb:.0f} MB"
