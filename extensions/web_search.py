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
    

if __name__ == "__main__":
    import sys
    import time
    sys.stdout.reconfigure(encoding="utf-8")
    log: list[str] = []
    def ok(label: str, cond: bool) -> None:
        log.append(f"  {'OK ' if cond else 'ZLE'} {label}")

    print("--- offline ---")
    hits = [SearchHit(f"T{i}", f"https://x/{i}", f"úryvok {i}") for i in range(5)]
    picked = _choose(hits, [None, "text 1", None, "text 3", "text 4"], 3)
    ok("stránky s textom majú prednosť, poradie vyhľadávača, čísla od 1",
       [(s.n, s.url[-1], s.full) for s in picked] == [(1, "1", True), (2, "3", True), (3, "4", True)])
    picked = _choose(hits, [None, "text 1", None, None, None], 3)
    ok("málo textov → doplnia sa úryvky v poradí",
       [(s.url[-1], s.full) for s in picked] == [("0", False), ("1", True), ("2", False)])
    picked = _choose(hits[:2], [None, None], 3)
    ok("menej výsledkov než stránok → toľko, koľko je", [s.text for s in picked] == ["úryvok 0", "úryvok 1"])
    ok("bez textu aj úryvku sa zdroj vynechá",
       _choose([SearchHit("a", "https://a", ""), SearchHit("b", "https://b", "u")], [None, None], 3)[0].url == "https://b")
    long = "Prvá veta. " * 400 + "\n\n" + "x" * 3000
    cut = cut_text(long, 2000)
    ok(f"cut_text skráti na hranici vety ({len(cut)} ≤ 2000, končí bodkou)", len(cut) <= 2000 and cut.endswith("."))
    ok("cut_text krátky text nechá", cut_text("ahoj", 10) == "ahoj")
    ok("cut_text bez hraníc → …", cut_text("y" * 50, 10) == "y" * 10 + "…")
    stop = threading.Event(); stop.set()
    ok("zrušené pred sťahovaním → []", gather("q", cancel=stop, searcher=lambda q: hits, fetcher=lambda *a, **k: "t") == [])
    def slow(url, cancel=None):
        time.sleep(0.05 if url.endswith(("0", "1")) else 10)
        return "obsah " * 100
    start = time.monotonic()
    picked = gather("q", searcher=lambda q: hits, fetcher=slow)
    took = time.monotonic() - start
    ok(f"pomalé stránky sa nečakajú: {took:.1f} s ≤ {WEB_FETCH_DEADLINE_S + 0.5} s, 2 texty + 1 úryvok",
       took <= WEB_FETCH_DEADLINE_S + 0.5 and [s.full for s in picked] == [True, True, False])
    def fast(url, cancel=None):
        return "obsah " * 100
    start = time.monotonic()
    gather("q", searcher=lambda q: hits, fetcher=fast)
    ok(f"rýchle stránky → bez čakania na termín ({time.monotonic() - start:.2f} s)", time.monotonic() - start < 1)
    def boom(q): raise WebSearchError("test")
    try:
        gather("q", searcher=boom); ok("chyba vyhľadávača prejde von ako WebSearchError", False)
    except WebSearchError:
        ok("chyba vyhľadávača prejde von ako WebSearchError", True)
    ok("fetch_text na neexistujúcu doménu → None, bez výnimky",
       fetch_text("https://neexistuje.invalid/", timeout=3) is None)
    print("\n".join(log))
    failed = any("ZLE" in line for line in log)
    log.clear()

    query = " ".join(sys.argv[1:]) or "Žilinská univerzita fakulta elektrotechniky"
    print(f"\n--- živý test: {query!r} ---")
    steps: list[str] = []
    start = time.monotonic()
    try:
        sources = gather(query, progress=steps.append)
    except WebSearchError as exc:
        print(f"  WebSearchError: {exc.message} | {exc.detail}")
    else:
        print(f"  {time.monotonic() - start:.1f} s, priebeh: {steps}")
        for s in sources:
            print(f"  [{s.n}] {'text ' if s.full else 'úryvok'} {len(s.text):5} zn. | {s.title[:50]} | {s.url[:60]}")
        ok("aspoň jeden zdroj", bool(sources))
        ok("čísla 1..n", [s.n for s in sources] == list(range(1, len(sources) + 1)))
        ok("aspoň jeden zdroj s textom stránky", any(s.full for s in sources))
        ok(f"žiadny zdroj nad {WEB_SOURCE_CHARS} znakov", all(len(s.text) <= WEB_SOURCE_CHARS + 1 for s in sources))
        print("\n".join(log))
    failed = failed or any("ZLE" in line for line in log)
    print("exit", 1 if failed else 0)
