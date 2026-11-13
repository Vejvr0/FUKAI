# --- ./core/context.py ---


from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from core.constants import (
    ATTACHMENT_CLOSE, ATTACHMENT_CUT_NOTE, ATTACHMENT_OPEN, TOKENS_PER_MESSAGE, PROMPT_RESERVE,
    WEB_CLOSE, WEB_CONTEXT_SHARE, WEB_INSTRUCTION, WEB_MIN_SOURCE_TOKENS, WEB_OPEN, WEB_SOURCE_HEAD
)
from core.errors import ContextOverflowError

__all__ = [
    "HistoryItem",
    "with_attachments",
    "AttachmentItem",
    "fit_attachments",
    "WebItem",
    "with_web",
    "fit_web",
    "cut_text",
    "PromptPlan",
    "fill_tokens",
    "build_prompt"
]


@dataclass(frozen=True)
class HistoryItem:
    id: int
    role: str
    text: str
    tokens: int | None


@dataclass(frozen=True)
class PromptPlan:
    messages: list[dict]
    counted: dict[int, int]
    dropped: list[int]
    prompt_tokens: int
    budget: int
    web_used: list[int] = field(default_factory=list)
    attachments: list[tuple[str, str, bool]] = field(default_factory=list)


WebItem = tuple[int, str, str, str]


def with_attachments(question: str, attachments: list[tuple[str, str]]) -> str:
    if not attachments:
        return question
    blocks = [f"{ATTACHMENT_OPEN.format(title=title)}\n{text}\n{ATTACHMENT_CLOSE}" for title, text in attachments]
    return "\n\n".join(blocks + ([question] if question else []))


AttachmentItem = tuple[str, str]


def fit_attachments(question: str, attachments: list[AttachmentItem], limit: int, count: Callable[[str], int]) -> list[tuple[str, str, bool]]:
    costs = [count(text) for _, text in attachments]
    frame = count(with_attachments(question, [(title, "") for title, _ in attachments]))
    if frame + sum(costs) <= limit and count(with_attachments(question, attachments)) <= limit:
        return [(title, text, False) for title, text in attachments]
    note = ATTACHMENT_CUT_NOTE.strip()
    room = limit - frame - count(note) * len(attachments)
    for _ in range(4):
        shares = _water_fill(costs, max(0, room))
        fitted = []
        for (title, text), share, cost in zip(attachments, shares, costs):
            if share >= cost:
                fitted.append((title, text, False))
            elif share <= 0:
                fitted.append((title, note, True))
            else:
                fitted.append((title, _cut_tokens(text, share, cost, count) + ATTACHMENT_CUT_NOTE, True))
        total = count(with_attachments(question, [(title, text) for title, text, _ in fitted]))
        if total <= limit:
            return fitted
        room -= total - limit + 8
    return [(title, note, True) for title, _ in attachments]


def with_web(question: str, sources: list[WebItem]) -> str:
    if not sources:
        return question
    blocks = [f"{WEB_SOURCE_HEAD.format(n=n, title=title, url=url)}\n{text}".rstrip() for n, title, url, text in sources]
    web = "\n\n".join([WEB_OPEN, *blocks, WEB_CLOSE, WEB_INSTRUCTION])
    return f"{web}\n\n{question}" if question else web


def cut_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = text[:limit]
    for mark in ("\n\n", "\n", ". "):
        at = head.rfind(mark)
        if at >= limit * 4 // 5:
            return head[:at + (1 if mark == ". " else 0)].rstrip()
    return head.rstrip() + "…"


def fit_web(sources: list[WebItem], limit: int, count: Callable[[str], int]) -> list[WebItem]:
    keep = list(sources)
    costs = {n: count(text) for n, _, _, text in keep}
    while keep:
        room = limit - count(with_web("", [(n, title, url, "") for n, title, url, _ in keep]))
        if room > 0:
            shares = _water_fill([costs[n] for n, *_ in keep], room)
            if all(share >= min(costs[n], WEB_MIN_SOURCE_TOKENS) for share, (n, *_) in zip(shares, keep)):
                return [(n, title, url, _cut_tokens(text, share, costs[n], count))
                        for share, (n, title, url, text) in zip(shares, keep)]
        keep.pop()
    return []


def _water_fill(costs: list[int], room: int) -> list[int]:
    shares = [0] * len(costs)
    left = room
    for k, i in enumerate(sorted(range(len(costs)), key=costs.__getitem__)):
        shares[i] = min(costs[i], left // (len(costs) - k))
        left -= shares[i]
    return shares


def _cut_tokens(text: str, share: int, cost: int, count: Callable[[str], int]) -> str:
    if cost <= share:
        return text
    chars = len(text) * share // cost
    for _ in range(6):
        cut = cut_text(text, chars)
        if count(cut) <= share:
            return cut
        chars = chars * 9 // 10
    return cut_text(text, chars)


def fill_tokens(history: list[HistoryItem], count: Callable[[str], int]) -> tuple[list[HistoryItem], dict[int, int]]:
    counted: dict[int, int] = {}
    filled_history: list[HistoryItem] = []

    for item in history:
        if item.tokens is None:
            tokens = count(item.text)
            counted[item.id] = tokens
            filled_history.append(replace(item, tokens=tokens))
        else:
            filled_history.append(item)

    return filled_history, counted


def build_prompt(history: list[HistoryItem], question: str, *, system_prompt: str, n_ctx: int, max_tokens: int, count: Callable[[str], int], web: list[WebItem] = (), attachments: list[AttachmentItem] = ()) -> PromptPlan:
    history, counted = fill_tokens(history, count)
    budget = n_ctx - max_tokens - PROMPT_RESERVE
    system_cost = (count(system_prompt) + TOKENS_PER_MESSAGE) if system_prompt else 0
    question_cost = count(question) + TOKENS_PER_MESSAGE
    fixed = system_cost + question_cost

    if fixed > budget:
        raise ContextOverflowError(
            f"systém {system_cost} + otázka {question_cost} tokenov, rozpočet {budget} (n_ctx={n_ctx}, max_tokens={max_tokens}, rezerva={PROMPT_RESERVE})",
            hint="Skráť správu, zvýš dĺžku kontextu alebo zníž maximálny počet tokenov odpovede."
        )
    
    sent: list[tuple[str, str, bool]] = []
    if attachments:
        sent = fit_attachments(question, list(attachments), budget - system_cost - TOKENS_PER_MESSAGE, count)
        question = with_attachments(question, [(title, text) for title, text, _ in sent])
        question_cost = count(question) + TOKENS_PER_MESSAGE
        fixed = system_cost + question_cost
        if fixed > budget:
            raise ContextOverflowError(
                f"systém {system_cost} + otázka s {len(sent)} prílohami {question_cost} tokenov, rozpočet {budget}",
                hint="Odober niektoré prílohy, zvýš dĺžku kontextu alebo zníž maximálny počet tokenov odpovede."
            )
    
    usable = history
    while usable and usable[-1].role != "assistant":
        usable = usable[:-1]

    web_used: list[int] = []
    if web:
        free = budget - fixed
        history_need = sum(item.tokens + TOKENS_PER_MESSAGE for item in usable)
        fitted = fit_web(list(web), max(int(free * WEB_CONTEXT_SHARE), free - history_need), count)
        if fitted:
            full = with_web(question, fitted)
            full_cost = count(full) + TOKENS_PER_MESSAGE
            if system_cost + full_cost <= budget:
                question, question_cost = full, full_cost
                fixed = system_cost + question_cost
                web_used = [n for n, *_ in fitted]

    remaining = budget - fixed
    start = len(usable)

    for index in range(len(usable) -1, -1, -1):
        cost = usable[index].tokens + TOKENS_PER_MESSAGE
        if cost > remaining:
            break
        remaining -= cost
        start = index

    while start < len(usable) and usable[start].role != "user":
        start += 1

    kept = usable[start:]
    kept_ids = {item.id for item in kept}
    messages: list[dict] = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend({"role": item.role, "content": item.text} for item in kept)
    messages.append({"role": "user", "content": question})
    history_cost = sum(item.tokens + TOKENS_PER_MESSAGE for item in kept)

    return PromptPlan(
        messages=messages,
        counted=counted,
        dropped=[item.id for item in history if item.id not in kept_ids],
        prompt_tokens=fixed + history_cost,
        budget=budget,
        web_used=web_used,
        attachments=sent
    )
