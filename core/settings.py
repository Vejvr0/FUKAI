from __future__ import annotations
from dataclasses import dataclass, replace
from pathlib import Path
from core.hardware import HardwareProfile
from core.errors import ModelNotFoundError, ModelFormatError
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


def _clamp(v, l, h):
    return max(l, min(h, v))


@dataclass(frozen=True)
class LoadParams:
    model_path: Path
    n_ctx: int = N_CTX_DEFAULT
    n_gpu_layers: int = 0
    n_threads: int | None = None
    n_batch: int = N_BATCH_DEFAULT
    use_mmap: bool = USE_MMAP_DEFAULT
    
    
    def __post_init__(self) -> None:
        object.__setattr__(self, "model_path", Path(self.model_path))
    
    
    @classmethod
    def for_hardware(cls, model_path: Path, hw: HardwareProfile, *, n_ctx: int = N_CTX_DEFAULT) -> LoadParams:
        return cls(
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=hw.n_gpu_layers,
            n_threads=hw.n_threads,
        )
    
    
    def clamped(self) -> LoadParams:
        return replace(
            self,
            n_ctx=_clamp(self.n_ctx, N_CTX_MIN, N_CTX_MAX),
            n_batch=_clamp(self.n_batch, N_BATCH_MIN, N_BATCH_MAX),
            n_gpu_layers=max(N_GPU_LAYERS_MIN, self.n_gpu_layers),
            n_threads=None if self.n_threads is None else max(N_THREADS_MIN, self.n_threads),
        )
    
    
    @property
    def model_size_mb(self) -> int:
        try:
            return self.model_path.stat().st_size // (1024 * 1024)
        except OSError:
            return 0
    
    
    @property
    def on_gpu(self) -> bool:
        return self.n_gpu_layers != 0
    
    
    def validate(self) -> None:
        path = self.model_path
        if not path.is_file():
            raise ModelNotFoundError(f"súbor neexistuje: {path}")
        if path.suffix.lower() != GGUF_SUFFIX:
            raise ModelFormatError(f"prípona {path.suffix!r}, očakávaná {GGUF_SUFFIX}: {path}")
        with path.open("rb") as f:
            if f.read(4) != b"GGUF":
                raise ModelFormatError(f"chýba GGUF hlavička: {path}")


@dataclass(frozen=True)
class SamplingParams:
    temperature: float = TEMPERATURE_DEFAULT
    max_tokens: int = MAX_TOKENS_DEFAULT
    top_p: float = TOP_P_DEFAULT
    top_k: int = TOP_K_DEFAULT
    repeat_penalty: float = REPEAT_PENALTY_DEFAULT
    seed: int | None = SEED_DEFAULT
    stop: tuple[str, ...] = STOP_DEFAULT
    
    
    def clamped(self) -> SamplingParams:
        return replace(
            self,
            temperature=_clamp(self.temperature, TEMPERATURE_MIN, TEMPERATURE_MAX),
            max_tokens=_clamp(self.max_tokens, MAX_TOKENS_MIN, MAX_TOKENS_MAX),
            top_p=_clamp(self.top_p, TOP_P_MIN, TOP_P_MAX),
            top_k=_clamp(self.top_k, TOP_K_MIN, TOP_K_MAX),
            repeat_penalty=_clamp(self.repeat_penalty, REPEAT_PENALTY_MIN, REPEAT_PENALTY_MAX),
            seed=None if self.seed is None else _clamp(self.seed, SEED_MIN, SEED_MAX),
            stop=tuple(self.stop)
        )


@dataclass(frozen=True)
class ChatParams:
    system_prompt: str = SYSTEM_PROMPT_DEFAULT
    web_search: bool = WEB_SEARCH_DEFAULT