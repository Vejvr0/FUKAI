# --- ./extensions/web_search.py ---


from __future__ import annotations
import threading
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from core.constants import (
    WEB_FETCH_DEADLINE_S, WEB_MAX_PAGE_BYTES, WEB_MAX_RESULTS, WEB_MIN_TEXT_CHARS,
    WEB_PAGE_TIMEOUT_S, WEB_PAGES, WEB_REGION, WEB_SAFESEARCH, WEB_SOURCE_CHARS,
    WEB_TIMEOUT_S, WEB_USER_AGENT
)
from core.context import cut_text
from core.errors import WebSearchError

__all__ = [
    "SearchHit",
    "WebSource",
    "search",
    "fetch_text",
    "gather",
]

_HTML_TYPES = ("text/html", "application/xhtml+xml")


@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    snippet: str


@dataclass(frozen=True)
class WebSource:
    n: int
    title: str
    url: str
    text: str
    full: bool


def search(query: str, *, max_results: int = WEB_MAX_RESULTS, region:  str = WEB_REGION, timeout: int = WEB_TIMEOUT_S) -> list[SearchHit]:
    try:
        from ddgs import DDGS
    except ImportError as exc:
        raise WebSearchError(
            f"{type(exc).__name__}: {exc}",
            hint="Chýba knižnica ddgs – nainštaluj requirements.txt."
        ) from exc
    
    try:
        rows = DDGS(timeout=timeout).text(query, region=region, safesearch=WEB_SAFESEARCH, max_results=max_results)
    except Exception as exc:
        raise WebSearchError(f"{type(exc).__name__}: {exc}") from exc
    
    hits: list[SearchHit] = []
    seen: set[str] = set()
    for row in rows or ():
        url = (row.get("href") or "").strip()
        if not url.startswith(("http://", "https://")) or url in seen:
            continue
        seen.add(url)
        hits.append(SearchHit((row.get("title") or url).strip(), url, (row.get("body") or "").strip()))
    if not hits:
        raise WebSearchError(
            f"žiadne výsledky pre {query!r}",
            message="Vyhľadávanie na webe nenašlo žiadne výsledky."
        )
    return hits


def fetch_text(url: str, *, timeout: float | tuple[float, float] = WEB_PAGE_TIMEOUT_S, max_bytes: int = WEB_MAX_PAGE_BYTES, cancel: threading.Event | None = None) -> str | None:
    import requests
    import trafilatura
    
    try:
        with requests.get(url, timeout=timeout, stream=True, headers={"User-Agent": WEB_USER_AGENT, "Accept-Language": "sk,cs;q=0.8,en;q=0.5"}) as response:
            if response.status_code != 200:
                return None
            if not response.headers.get("Content-Type", "").lower().startswith(_HTML_TYPES):
                return None
            body = bytearray()
            for chunk in response.iter_content(64 * 1024):
                if cancel is not None and cancel.is_set():
                    return None
                body.extend(chunk)
                if len(body) >= max_bytes:
                    break
            encoding = response.encoding or response.apparent_encoding or "utf-8"
        html = bytes(body).decode(encoding, errors="replace")
        text = trafilatura.extract(html, url=url, include_comments=False, include_tables=True, favor_precision=True)
    except Exception:
        return None
    
    text = (text or "").strip()
    return text if len(text) >= WEB_MIN_TEXT_CHARS else None


def gather(
    query: str,
    *,
    pages: int = WEB_PAGES,
    cancel: threading.Event | None = None,
    progress: Callable[[str], None] | None = None,
    searcher: Callable[[str], list[SearchHit]] = search,
    fetcher: Callable[..., str | None] = fetch_text
) -> list[WebSource]:
    if progress:
        progress("Hľadám na webe…")
    hits = searcher(query)
    if cancel is not None and cancel.is_set():
        return []
    if progress:
        progress(f"Čítam {min(len(hits), pages)} {_pages_word(min(len(hits), pages))}…")
    texts = _fetch_all(hits, pages, cancel, fetcher)
    if cancel is not None and cancel.is_set():
        return []
    return _choose(hits, texts, pages)


def _fetch_all(hits: list[SearchHit], pages: int, cancel: threading.Event | None, fetcher: Callable[..., str | None]) -> list[str | None]:
    texts: list[str | None] = [None] * len(hits)
    pool = ThreadPoolExecutor(max_workers=len(hits))
    futures = {pool.submit(fetcher, hit.url, cancel=cancel): i for i, hit in enumerate(hits)}
    pending = set(futures)
    deadline = time.monotonic() + WEB_FETCH_DEADLINE_S
    
    try:
        while pending:
            left = deadline - time.monotonic()
            if left <= 0 or (cancel is not None and cancel.is_set()):
                break
            done, pending = wait(pending, timeout=min(left, 0.2), return_when=FIRST_COMPLETED)
            for future in done:
                texts[futures[future]] = future.result()
            finished = [futures[f] for f in futures if f.done()]
            if all(i in finished for i in range(min(pages, len(hits)))) and all(texts[:pages]):
                break
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
        
    return texts


def _choose(hits: list[SearchHit], texts: list[str | None], pages: int) -> list[WebSource]:
    with_text = [i for i, text in enumerate(texts) if text][:pages]
    snippets = [i for i, hit in enumerate(hits) if i not in with_text and hit.snippet]
    chosen = sorted(with_text + snippets[:pages - len(with_text)])
    return [WebSource(n, hits[i].title, hits[i].url, cut_text(texts[i] or hits[i].snippet, WEB_SOURCE_CHARS), full=bool(texts[i])) for n, i in enumerate(chosen, start=1)]


def _pages_word(count: int) -> str:
    return "stránku" if count == 1 else "stránky" if count < 5 else "stránok"
