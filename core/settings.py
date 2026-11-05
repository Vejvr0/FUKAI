from __future__ import annotations
from dataclasses import dataclass, replace, fields
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
    "ChatParams",
    "ChatProperties",
    "ModelMeta"
]

_NOT_STORED = frozenset({"model_path"})


def _clamp(v, l, h):
    return max(l, min(h, v))


def _known(cls, data: dict) -> dict:
    allowed = {f.name for f in fields(cls)} - _NOT_STORED
    return {k: v for k, v in data.items() if k in allowed}


def _as_dict(obj) -> dict:
    return {f.name: getattr(obj, f.name) for f in fields(obj) if f.name not in _NOT_STORED}


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


    def to_dict(self) -> dict:
        return _as_dict(self)


    @classmethod
    def from_dict(cls, data: dict, model_path) -> LoadParams:
        return cls(model_path=model_path, **_known(cls, data)).clamped()
    
    
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


    def to_dict(self) -> dict:
        return _as_dict(self)


    @classmethod
    def from_dict(cls, data: dict) -> SamplingParams:
        return cls(**_known(cls, data)).clamped()
    
    
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


    def to_dict(self) -> dict:
        return _as_dict(self)


    @classmethod
    def from_dict(cls, data: dict) -> ChatParams:
        return cls(**_known(cls, data))


@dataclass(frozen=True)
class ModelMeta:
    arch: str | None = None
    n_ctx_train: int | None = None
    n_layers: int | None = None
    name: str | None = None
    quant: str | None = None
    size_label: str | None = None
    has_chat_template: bool | None = None
    n_head_kv: int | None = None
    head_dim_k: int | None = None
    head_dim_v: int | None = None

    def to_dict(self) -> dict:
        return _as_dict(self)


    @classmethod
    def from_dict(cls, data: dict) -> ModelMeta:
        return cls(**_known(cls, data))


@dataclass(frozen=True)
class ChatProperties:
    load: LoadParams
    sampling: SamplingParams = SamplingParams()
    chat: ChatParams = ChatParams()


    @classmethod
    def defaults_for(cls, model_path, hw: HardwareProfile, *, meta: ModelMeta | None = None) -> ChatProperties:
        n_ctx = N_CTX_DEFAULT
        if meta is not None and meta.n_ctx_train:
            n_ctx = min(n_ctx, meta.n_ctx_train)
        return cls(load=LoadParams.for_hardware(model_path, hw, n_ctx=n_ctx))


    def to_dict(self) -> dict:
        return {
            "load": self.load.to_dict(),
            "sampling": self.sampling.to_dict(),
            "chat": self.chat.to_dict()
        }


    @classmethod
    def from_dict(cls, data: dict, model_path) -> ChatProperties:
        return cls(
            load=LoadParams.from_dict(data.get("load") or {}, model_path),
            sampling=SamplingParams.from_dict(data.get("sampling") or {}),
            chat=ChatParams.from_dict(data.get("chat") or {})
        )


    def needs_reload(self, other: ChatProperties) -> bool:
        return self.load.clamped() != other.load.clamped()


if __name__ == "__main__":
    import json
    import sys
    import tempfile
    from core.hardware import detect

    sys.stdout.reconfigure(encoding="utf-8")

    hw = detect()
    model = "models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"

    print("--- predvolené hodnoty pre model ---")
    print(f"hardvér:      backend={hw.backend}  n_threads={hw.n_threads}  "
          f"n_gpu_layers={hw.n_gpu_layers}")
    props = ChatProperties.defaults_for(model, hw, meta=ModelMeta("llama", 32768, 32))
    print(f"meta 32768:   n_ctx={props.load.n_ctx} (predvolené {N_CTX_DEFAULT} sa zmestí)")
    print(f"meta 2048:    n_ctx="
          f"{ChatProperties.defaults_for(model, hw, meta=ModelMeta('llama', 2048, 32)).load.n_ctx}"
          f" (orezané na možnosti modelu)")
    print(f"bez meta:     n_ctx={ChatProperties.defaults_for(model, hw).load.n_ctx}")
    print(f"prázdna meta: n_ctx={ChatProperties.defaults_for(model, hw, meta=ModelMeta()).load.n_ctx}"
          f" (n_ctx_train je None, nie 0)")

    print("\n--- blob pre properties.data ---")
    blob = props.to_dict()
    print(f"skupiny:      {list(blob)}")
    for group, values in blob.items():
        print(f"{group + ':':<14}{values}")
    print(f"model_path:   {'JE V BLOBE!' if 'model_path' in blob['load'] else 'nie je (§7.2)'}")

    print("\n--- round-trip cez JSON ---")
    back = ChatProperties.from_dict(json.loads(json.dumps(blob)), model)
    print(f"rovnaké:      {back == props}")
    print(f"stop:         {type(props.sampling.stop).__name__} → JSON "
          f"{type(json.loads(json.dumps(blob))['sampling']['stop']).__name__} → "
          f"{type(back.sampling.stop).__name__}")

    print("\n--- blob z inej verzie appky ---")
    dirty = ChatProperties.from_dict(
        {"load": {"n_ctx": 99, "neznamy_kluc": 1, "model_path": "C:/zly.gguf"},
         "sampling": {"temperature": 9.9, "stop": ["</s>"]}},
        model,
    )
    print(f"n_ctx 99:     {dirty.load.n_ctx} (orezané na N_CTX_MIN)")
    print(f"temp 9.9:     {dirty.sampling.temperature} (orezaná na TEMPERATURE_MAX)")
    print(f"kľúč navyše:  zahodený, n_batch={dirty.load.n_batch} je predvolený")
    print(f"model_path:   {dirty.load.model_path.name} (z argumentu, nie z blobu)")
    print(f"stop:         {dirty.sampling.stop}")
    print(f'"load": null: n_ctx={ChatProperties.from_dict({"load": None}, model).load.n_ctx}')
    print(f"prázdny blob: n_ctx={ChatProperties.from_dict({}, model).load.n_ctx}")

    print("\n--- needs_reload ---")
    other_ctx = replace(props, load=replace(props.load, n_ctx=8192))
    other_temp = replace(props, sampling=replace(props.sampling, temperature=0.1))
    small = replace(props, load=replace(props.load, n_ctx=99))
    clamped_min = replace(props, load=replace(props.load, n_ctx=256))
    print(f"n_ctx 4096→8192:     {props.needs_reload(other_ctx)}")
    print(f"temperature 0.7→0.1: {props.needs_reload(other_temp)}")
    print(f"n_ctx 99 vs 256:     {small.needs_reload(clamped_min)} (obe strany orezané)")

    print("\n--- validate() ---")
    with tempfile.TemporaryDirectory() as tmp:
        good = Path(tmp) / "model.gguf"
        good.write_bytes(b"GGUF" + b"\x00" * 60)
        bad_header = Path(tmp) / "hlavicka.gguf"
        bad_header.write_bytes(b"ZIP!" + b"\x00" * 60)
        bad_suffix = Path(tmp) / "model.bin"
        bad_suffix.write_bytes(b"GGUF" + b"\x00" * 60)

        for path in (good, bad_header, bad_suffix, Path(tmp) / "niet.gguf"):
            try:
                LoadParams(path).validate()
                result = "OK"
            except (ModelNotFoundError, ModelFormatError) as exc:
                result = f"{type(exc).__name__}: {exc.message}"
            print(f"{path.name:<14}{result}")

    print("\n--- ModelMeta ---")
    meta = ModelMeta("llama", 32768, 32)
    print(f"to_dict:      {meta.to_dict()}")
    print(f"round-trip:   {ModelMeta.from_dict(json.loads(json.dumps(meta.to_dict()))) == meta}")
    print(f"prázdny dict: {ModelMeta.from_dict({})}")