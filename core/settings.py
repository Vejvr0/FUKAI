from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from core.errors import ModelFormatError, ModelNotFoundError
from core.hardware import HardwareProfile

__all__ = [
    "GGUF_SUFFIX",
    "LoadParams",
    "SamplingParams",
]

GGUF_SUFFIX = ".gguf"


def _clamp(value, low, high):
    return max(low, min(high, value))


@dataclass(frozen=True)
class LoadParams:
    """Parametre modelu, ktorých zmena si vyžaduje reload.

    Tieto hodnoty vstupujú do konštruktora `Llama(...)`, takže sa nedajú zmeniť
    počas života načítaného modelu – UI pri ich zmene ponúka „Použiť a reloadnúť“.
    Pozri ALMANAC §7.
    """

    model_path: Path
    n_ctx: int = 4096
    n_gpu_layers: int = 0       # 0 = iba CPU, -1 = všetko na GPU, n = čiastočný offload
    n_threads: int = 4          # = cores_performance, pozri ALMANAC §4
    n_batch: int = 512
    use_mmap: bool = True

    # hranice pre UI aj pre ozdravenie hodnôt z databázy
    N_CTX_MIN = 256
    N_CTX_MAX = 131072
    N_BATCH_MIN = 32
    N_BATCH_MAX = 4096

    @classmethod
    def for_hardware(
        cls,
        model_path: str | Path,
        profil: HardwareProfile,
        **over,
    ) -> LoadParams:
        """Predvolené parametre podľa detegovaného hardvéru.

        `n_threads` aj `n_gpu_layers` berie z profilu, nie z `psutil` priamo –
        profil už rieši P/E jadrá a chýbajúcu GPU.
        """
        return cls(
            model_path=Path(model_path),
            n_threads=profil.n_threads,
            n_gpu_layers=profil.n_gpu_layers,
            **over,
        )

    def clamped(self) -> LoadParams:
        """Kópia s hodnotami v povolených hraniciach.

        Zámerne nie v `__post_init__` – oprava hodnôt má byť viditeľný krok,
        nie tichá zmena v konštruktore.
        """
        return replace(
            self,
            n_ctx=_clamp(int(self.n_ctx), self.N_CTX_MIN, self.N_CTX_MAX),
            n_batch=_clamp(int(self.n_batch), self.N_BATCH_MIN, self.N_BATCH_MAX),
            n_threads=max(1, int(self.n_threads)),
            n_gpu_layers=max(-1, int(self.n_gpu_layers)),
        )

    def validate(self) -> None:
        """Overí, že cesta vedie na existujúci `.gguf`. Inak vyhodí `ModelError`."""
        path = Path(self.model_path)
        if path.suffix.lower() != GGUF_SUFFIX:
            raise ModelFormatError(f"prípona {path.suffix or '(žiadna)'}, čaká sa {GGUF_SUFFIX}")
        if not path.is_file():
            raise ModelNotFoundError(f"cesta neexistuje alebo nie je súbor: {path}")

    @property
    def model_size_mb(self) -> int:
        """Veľkosť `.gguf` na disku, alebo 0 keď sa nedá zistiť."""
        try:
            return Path(self.model_path).stat().st_size // 1024 // 1024
        except OSError:
            return 0

    @property
    def on_gpu(self) -> bool:
        return self.n_gpu_layers != 0

    def to_dict(self) -> dict:
        """Na uloženie do SQLite (`chat_settings`) – `Path` ide ako text."""
        return {
            "model_path": str(self.model_path),
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "n_threads": self.n_threads,
            "n_batch": self.n_batch,
            "use_mmap": self.use_mmap,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LoadParams:
        return cls(
            model_path=Path(data["model_path"]),
            n_ctx=int(data.get("n_ctx", cls.n_ctx)),
            n_gpu_layers=int(data.get("n_gpu_layers", cls.n_gpu_layers)),
            n_threads=int(data.get("n_threads", cls.n_threads)),
            n_batch=int(data.get("n_batch", cls.n_batch)),
            use_mmap=bool(data.get("use_mmap", cls.use_mmap)),
        ).clamped()


@dataclass(frozen=True)
class SamplingParams:
    """Parametre jednej požiadavky na generovanie.

    Menia sa bez reloadu modelu – idú priamo do `create_chat_completion()`.
    """

    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 40
    repeat_penalty: float = 1.1
    max_tokens: int = 1024
    seed: int | None = None
    stop: tuple[str, ...] = ()

    TEMPERATURE_MAX = 2.0
    TOP_K_MAX = 1000
    REPEAT_PENALTY_MIN = 1.0
    REPEAT_PENALTY_MAX = 2.0
    MAX_TOKENS_MIN = 1

    def clamped(self) -> SamplingParams:
        return replace(
            self,
            temperature=_clamp(float(self.temperature), 0.0, self.TEMPERATURE_MAX),
            top_p=_clamp(float(self.top_p), 0.0, 1.0),
            top_k=_clamp(int(self.top_k), 0, self.TOP_K_MAX),
            repeat_penalty=_clamp(
                float(self.repeat_penalty), self.REPEAT_PENALTY_MIN, self.REPEAT_PENALTY_MAX
            ),
            max_tokens=max(self.MAX_TOKENS_MIN, int(self.max_tokens)),
        )

    def to_dict(self) -> dict:
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repeat_penalty": self.repeat_penalty,
            "max_tokens": self.max_tokens,
            "seed": self.seed,
            "stop": list(self.stop),
        }

    @classmethod
    def from_dict(cls, data: dict) -> SamplingParams:
        seed = data.get("seed")
        return cls(
            temperature=float(data.get("temperature", cls.temperature)),
            top_p=float(data.get("top_p", cls.top_p)),
            top_k=int(data.get("top_k", cls.top_k)),
            repeat_penalty=float(data.get("repeat_penalty", cls.repeat_penalty)),
            max_tokens=int(data.get("max_tokens", cls.max_tokens)),
            seed=None if seed is None else int(seed),
            stop=tuple(data.get("stop") or ()),
        ).clamped()
