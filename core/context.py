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


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    def words(text: str) -> int:
        """Falosne pocitadlo: 1 slovo = 1 token, takze cisla su rucne overitelne."""
        return len(text.split())

    def chat(n: int, tokens: int | None = 10) -> list[HistoryItem]:
        """n sprav striedavo user/assistant, kazda 10 slov."""
        return [
            HistoryItem(
                i + 1,
                "user" if i % 2 == 0 else "assistant",
                " ".join(f"s{i + 1}w{w}" for w in range(10)),
                tokens,
            )
            for i in range(n)
        ]

    def show(plan: PromptPlan) -> None:
        roles = " ".join(m["role"][0] for m in plan.messages)
        print(f"  role:         {roles}")
        print(f"  tokeny:       {plan.prompt_tokens} / rozpocet {plan.budget}"
              f"  {'OK' if plan.prompt_tokens <= plan.budget else 'PRETEKA!'}")
        print(f"  zahodene:     {plan.dropped}")
        print(f"  dopocitane:   {plan.counted}")

    print(f"TOKENS_PER_MESSAGE={TOKENS_PER_MESSAGE}  PROMPT_RESERVE={PROMPT_RESERVE}")

    print("\n--- vsetko sa vojde ---")
    plan = build_prompt(chat(4), "ako sa mas", system_prompt="bud strucny",
                        n_ctx=2048, max_tokens=256, count=words)
    show(plan)
    print(f"  posledna:     {plan.messages[-1]}")

    print("\n--- prazdny system prompt ---")
    plan = build_prompt(chat(2), "ako sa mas", system_prompt="",
                        n_ctx=2048, max_tokens=256, count=words)
    print(f"  role:         {' '.join(m['role'] for m in plan.messages)}  (bez system spravy)")

    print("\n--- orezanie: 6 sprav, rozpocet na 2 ---")
    # budget = 200 - 50 - 64 = 86; fixed = (2+8) + (3+8) = 21; na historiu 65 => 3 x 18 = 54,
    # ale 3. najstarsia ponechana je assistant, takze sa zahodi tiez => zostanu 2 (36)
    plan = build_prompt(chat(6), "ako sa mas", system_prompt="bud strucny",
                        n_ctx=200, max_tokens=50, count=words)
    show(plan)
    print(f"  prva ponechana je user: {plan.messages[1]['role'] == 'user'}")

    print("\n--- visiaca otazka na konci historie (pad pocas generovania) ---")
    plan = build_prompt(chat(3), "ako sa mas", system_prompt="",
                        n_ctx=2048, max_tokens=256, count=words)
    show(plan)
    print(f"  bez user, user: {['user', 'user'] != [m['role'] for m in plan.messages[-2:]]}")

    print("\n--- cache tokenov ---")
    mixed = [
        HistoryItem(1, "user", "a b c", None),
        HistoryItem(2, "assistant", "d e", 2),
        HistoryItem(3, "user", "f g h i", None),
        HistoryItem(4, "assistant", "j", 1),
    ]
    plan = build_prompt(mixed, "ako sa mas", system_prompt="",
                        n_ctx=2048, max_tokens=256, count=words)
    print(f"  dopocitane:   {plan.counted} (len tie s tokens=None)")
    filled, counted = fill_tokens(mixed, words)
    print(f"  fill_tokens:  {[i.tokens for i in filled]}  nove: {counted}")

    print("\n--- nezmesti sa ani otazka ---")
    for n_ctx, max_tokens, note in ((100, 50, "max_tokens >= n_ctx - rezerva"),
                                    (2048, 256, "velmi dlha otazka")):
        question = "ako sa mas" if n_ctx == 100 else " ".join(f"w{i}" for i in range(5000))
        try:
            build_prompt([], question, system_prompt="bud strucny",
                         n_ctx=n_ctx, max_tokens=max_tokens, count=words)
            print(f"  {note}: PRESLO?!")
        except ContextOverflowError as exc:
            print(f"  {note}:")
            print(f"    {exc.message}")
            print(f"    {exc}")

    print("\n--- web ---")
    bad: list[str] = []
    def ok(label: str, cond: bool) -> None:
        print(f"  {'OK ' if cond else 'ZLE'} {label}")
        if not cond:
            bad.append(label)

    def src(n: int, words_count: int) -> WebItem:
        return (n, f"Nadpis {n}", f"https://x/{n}", " ".join(f"z{n}w{i}." for i in range(words_count)))

    text = with_web("Kto je rektor?", [src(1, 3), src(2, 3)])
    ok("with_web: pokyn, [1] s adresou, otázka posledná",
       WEB_INSTRUCTION in text and "[1] Nadpis 1\nhttps://x/1" in text and text.endswith("\n\nKto je rektor?"))
    ok("with_web bez zdrojov = otázka", with_web("q", []) == "q")
    ok("cut_text: veta na konci vyhrá nad odsekom v polovici",
       cut_text("a" * 50 + "\n\n" + "b. " * 20, 100).endswith("b."))

    three = [src(1, 400), src(2, 400), src(3, 400)]
    overhead = words(with_web("", [(n, t, u, "") for n, t, u, _ in three]))
    fitted = fit_web(three, 10_000, words)
    ok("fit_web: všetko sa zmestí → texty bez zmeny", [f[3] for f in fitted] == [t[3] for t in three])
    fitted = fit_web([src(1, 50), src(2, 400), src(3, 400)], overhead + 450, words)
    shares = [words(f[3]) for f in fitted]
    ok(f"fit_web: krátky zdroj celý, dlhé po rovnakom diele {shares}",
       shares[0] == 50 and abs(shares[1] - shares[2]) <= 1 and 400 <= sum(shares) <= 450)
    ok("fit_web: spolu s hlavičkou najviac limit",
       words(with_web("", fitted)) <= overhead + 450)
    fitted = fit_web(three, overhead + 200, words)
    ok(f"fit_web: diel pod {WEB_MIN_SOURCE_TOKENS} → vynechá sa posledný ({[f[0] for f in fitted]})",
       [f[0] for f in fitted] == [1, 2])
    ok("fit_web: nezmestí sa nič → []", fit_web(three, 20, words) == [])

    # budget = 4096 - 1024 - 64 = 3008; otázka 3 + 8 → voľných 2997
    plan = build_prompt([], "kto je rektor", system_prompt="", n_ctx=4096, max_tokens=1024, count=words,
                        web=[src(1, 2000), src(2, 2000), src(3, 2000)])
    ok(f"bez histórie dostanú zdroje celé voľné miesto ({plan.prompt_tokens} / {plan.budget})",
       plan.prompt_tokens <= plan.budget and plan.prompt_tokens > plan.budget * 0.95 and plan.web_used == [1, 2, 3])
    ok("otázka je posledná a zdroje v tej istej správe",
       plan.messages[-1]["role"] == "user" and plan.messages[-1]["content"].endswith("kto je rektor")
       and "[3] Nadpis 3" in plan.messages[-1]["content"])

    long_chat = chat(400)                       # 400 × 18 = 7200 tokenov histórie
    plan = build_prompt(long_chat, "kto je rektor", system_prompt="", n_ctx=4096, max_tokens=1024,
                        count=words, web=[src(1, 2000), src(2, 2000), src(3, 2000)])
    web_cost = words(plan.messages[-1]["content"]) - 3
    free = plan.budget - 11
    ok(f"dlhý chat: zdroje {web_cost} ≈ 60 % z {free}, zvyšok histórii ({len(plan.messages) - 1} správ)",
       int(free * 0.6) * 0.9 <= web_cost <= int(free * 0.6) and len(plan.messages) > 60
       and plan.prompt_tokens <= plan.budget)
    plan = build_prompt(long_chat, "kto je rektor", system_prompt="", n_ctx=4096, max_tokens=1024,
                        count=words, web=[src(1, 30)])
    ok("krátky zdroj nezoberie histórii viac, než potrebuje",
       words(plan.messages[-1]["content"]) - 3 < 120 and plan.prompt_tokens <= plan.budget)
    plan = build_prompt(chat(4), "kto je rektor", system_prompt="", n_ctx=200, max_tokens=50,
                        count=words, web=three)
    ok(f"malý kontext: zdroje sa nezmestia → bez webu, web_used={plan.web_used}",
       plan.web_used == [] and plan.messages[-1]["content"] == "kto je rektor")
    plan = build_prompt(chat(4), "ahoj", system_prompt="", n_ctx=2048, max_tokens=256, count=words)
    ok("bez webu sa nič nemení", plan.web_used == [] and plan.messages[-1]["content"] == "ahoj")
    print("  web: " + ("všetko OK" if not bad else f"{len(bad)} ZLE"))

    if len(sys.argv) > 1:
        from core.hardware import detect
        from core.llm_engine import LlmEngine
        from core.settings import LoadParams, SamplingParams

        print(f"\n--- realny engine: {sys.argv[1]} ---")
        engine = LlmEngine()
        engine.load(LoadParams.for_hardware(sys.argv[1], detect(), n_ctx=2048))
        plan = build_prompt(
            chat(6, tokens=None), "Kolko sprav mas v kontexte?",
            system_prompt="Odpovedaj strucne po slovensky.",
            n_ctx=engine.n_ctx, max_tokens=64, count=engine.count_tokens,
        )
        show(plan)
        text = "".join(engine.stream(plan.messages, SamplingParams(max_tokens=64)))
        print(f"  odpoved:      {text.strip()[:120]}")
        print(f"  koniec:       {engine.finish_reason}")
        engine.unload()
