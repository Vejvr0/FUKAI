from __future__ import annotations
from dataclasses import dataclass, replace
from pathlib import Path
from core.constants import (
    N_CTX_MIN, N_CTX_MAX, N_CTX_DEFAULT,
    N_BATCH_MIN, N_BATCH_MAX, N_BATCH_DEFAULT,
    N_GPU_LAYERS_MIN, N_THREADS_MIN,
    TEMPERATURE_MIN, TEMPERATURE_MAX, TEMPERATURE_DEFAULT,
    TOP_P_MIN, TOP_P_MAX, TOP_P_DEFAULT,
    TOP_K_MIN, TOP_K_MAX, TOP_K_DEFAULT,
    REPEAT_PENALTY_MIN, REPEAT_PENALTY_MAX, REPEAT_PENALTY_DEFAULT,
    MAX_TOKENS_MIN, MAX_TOKENS_MAX, MAX_TOKENS_DEFAULT, USE_MMAP_DEFAULT,
    SEED_MIN, SEED_MAX, SEED_DEFAULT, STOP_DEFAULT,
    SYSTEM_PROMPT_DEFAULT, WEB_SEARCH_DEFAULT, GGUF_SUFFIX
)

__all__ = [
    "GGUF_SUFFIX",
    "LoadParams",
    "SamplingParams",
    "ChatParams"
]


@dataclass(frozen=True)
class LoadParams:
    model_path: Path
    n_ctx: int = N_CTX_DEFAULT
    n_gpu_layers: int = 0
    n_threads: int = None
    n_batch: int = N_BATCH_DEFAULT
    use_map: bool = USE_MMAP_DEFAULT


@dataclass(frozen=True)
class SamplingParams:
    temperature: float = TEMPERATURE_DEFAULT
    max_tokens: int = MAX_TOKENS_DEFAULT
    top_p: float = TOP_P_DEFAULT
    top_k: int = TOP_K_DEFAULT
    repeat_penalty: float = REPEAT_PENALTY_DEFAULT
    seed: int = SEED_DEFAULT
    stop: dict = STOP_DEFAULT


@dataclass(frozen=True)
class ChatParams:
    system_prompt: str = SYSTEM_PROMPT_DEFAULT
    web_search: bool = WEB_SEARCH_DEFAULT