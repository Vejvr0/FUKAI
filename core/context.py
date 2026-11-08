from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, replace
from core.constants import ATTACHMENT_CLOSE, ATTACHMENT_OPEN, TOKENS_PER_MESSAGE, PROMPT_RESERVE
from core.errors import ContextOverflowError

__all__ = [
    "HistoryItem",
    "with_attachments",
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


def with_attachments(question: str, attachments: list[tuple[str, str]]) -> str:
    """Text prílohy ide do **tej istej správy** ako otázka. Samostatná správa by rozbila
    striedanie rolí, na ktorom Gemma trvá (§8 krok 3), a história by sa orezávala po
    kusoch, ktoré k sebe patria."""
    if not attachments:
        return question
    blocks = [f"{ATTACHMENT_OPEN.format(title=title)}\n{text}\n{ATTACHMENT_CLOSE}"
              for title, text in attachments]
    return "\n\n".join(blocks + ([question] if question else []))


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


def build_prompt(history: list[HistoryItem], question: str, *, system_prompt: str, n_ctx: int, max_tokens: int, count: Callable[[str], int]) -> PromptPlan:
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
    usable = history
    while usable and usable[-1].role != "assistant":
        usable = usable[:-1]

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
        budget=budget
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
