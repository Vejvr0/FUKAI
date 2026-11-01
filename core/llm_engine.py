from __future__ import annotations
from collections.abc import Iterator
from enum import Enum
import threading
from types import ModuleType
from core.constants import MEMORY_MARGIN, META_ARCH, META_CONTEXT_LENGTH, META_BLOCK_COUNT
from core.hardware import detect_gpu, free_ram_mb
from core.settings import LoadParams, SamplingParams
from core.errors import (
    BackendUnavailableError,
    ModelLoadError,
    InsufficientMemoryError,
    GenerationError,
    ContextOverflowError,
    Notice,
)

__all__ = ["LlmEngine", "FinishReason"]

_CONTEXT_FAILED = "Failed to create llama_context"


def _import_llama() -> ModuleType:
    try:
        import llama_cpp
    except (ImportError, OSError) as exc:
        raise BackendUnavailableError(f"{type(exc).__name__}: {exc}") from exc
    return llama_cpp


def _memory_pool(params: LoadParams) -> tuple[int, str]:
    gpu = detect_gpu()
    ram = free_ram_mb()
    if params.n_gpu_layers == 0 or gpu is None or gpu.backend == "metal":
        return ram, "operačnej pamäte"
    if params.n_gpu_layers == -1:
        return gpu.vram_free_mb, "pamäte grafickej karty"
    return gpu.vram_free_mb + ram, "pamäte RAM a grafickej karty"


class FinishReason(Enum):
    DONE = "stop"
    LENGTH = "length"
    STOPPED = "user"


class LlmEngine:
    def __init__(self, *, verbose: bool = False) -> None:
        self.verbose = verbose
        self._llm = None
        self._params: LoadParams | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._finish_reason: FinishReason | None = None
        
        
    @property
    def is_loaded(self) -> bool:
        return self._llm is not None
    
    
    def _require_loaded(self):
        if self._llm is None:
            raise ModelLoadError("model nie je načítaný, najprv treba načítať model")
        return self._llm
    
    
    def load(self, params: LoadParams) -> list[Notice]:
        params = params.clamped()
        params.validate()
        llama = _import_llama()

        with self._lock:
            self._unload_locked()
            notices: list[Notice] = []
            need_mb = int(params.model_size_mb * MEMORY_MARGIN)
            free_mb, where = _memory_pool(params)
            if need_mb > free_mb:
                notices.append(Notice.warning(
                    f"Model potrebuje približne {need_mb / 1024:.1f} GB {where}, "
                    f"voľných je {free_mb / 1024:.1f} GB. Načítanie môže zlyhať alebo byť veľmi pomalé.",
                    hint="Zatvor iné aplikácie, zvoľ menší model alebo zníž dĺžku kontextu.",
                    detail=f"model {params.model_size_mb} MB x {MEMORY_MARGIN}, volne {free_mb} MB, n_gpu_layers={params.n_gpu_layers}",
                ))
            try:
                llm = llama.Llama(
                    model_path=str(params.model_path),
                    n_ctx=params.n_ctx,
                    n_gpu_layers=params.n_gpu_layers,
                    n_threads=params.n_threads,
                    n_batch=params.n_batch,
                    use_mmap=params.use_mmap,
                    verbose=self.verbose
                )
            except Exception as exc:
                detail = f"{type(exc).__name__}: {exc}"
                if _CONTEXT_FAILED in str(exc):
                    raise InsufficientMemoryError(
                        detail,
                        message=f"Na dĺžku kontextu {params.n_ctx} tokenov nie je dosť {where}.",
                        hint="Zníž dĺžku kontextu alebo uber vrstvy na GPU.",
                    ) from exc
                if need_mb > free_mb:
                    raise InsufficientMemoryError(
                        detail, needed_mb=need_mb, available_mb=free_mb, where=where,
                    ) from exc
                raise ModelLoadError(detail) from exc
            self._llm = llm
            self._params = params
            trained = self.n_ctx_train
            if trained is not None and params.n_ctx > trained:
                notices.append(Notice.warning(
                    f"Dĺžka kontextu {params.n_ctx} je väčšia, než na akú bol model trénovaný ({trained}).",
                    hint="Na dlhom kontexte môže model odpovedať nespoľahlivo.",
                ))
            return notices
    
    
    def unload(self) -> None:
        with self._lock:
            self._unload_locked()
    
    
    def _unload_locked(self) -> None:
        llm, self._llm, self._params = self._llm, None, None
        if llm is not None:
            llm.close()
    
    
    @property
    def n_ctx(self) -> int | None:
        llm = self._llm
        return None if llm is None else llm.n_ctx()
    
    
    @property
    def n_ctx_train(self) -> int | None:
        return self._meta_int(META_CONTEXT_LENGTH)
    
    
    @property
    def n_layers(self) -> int | None:
        return self._meta_int(META_BLOCK_COUNT)
    
    
    @property
    def n_layers_offloadable(self) -> int | None:
        layers = self.n_layers
        return None if layers is None else layers + 1
    
    
    def _meta_int(self, key: str) -> int | None:
        llm = self._llm
        if llm is None:
            return None
        arch = llm.metadata.get(META_ARCH)
        value = llm.metadata.get(f"{arch}.{key}")
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    
    
    def tokenize(self, text: str) -> list[int]:
        llm = self._require_loaded()
        return llm.tokenize(
            text.encode("utf-8"),
            add_bos=False,
            special=False
        )
    
    
    def count_tokens(self, text: str) -> int:
        return len(self.tokenize(text))
    
    
    def stream(self, messages: list[dict], sampling: SamplingParams) -> Iterator[str]:
        sampling = sampling.clamped()
        with self._lock:
            llm = self._require_loaded()
            self._stop.clear()
            self._finish_reason = None
            chunks = None
            try:
                chunks = llm.create_chat_completion(
                    messages=messages,
                    stream=True,
                    temperature=sampling.temperature,
                    top_p=sampling.top_p,
                    top_k=sampling.top_k,
                    repeat_penalty=sampling.repeat_penalty,
                    max_tokens=sampling.max_tokens,
                    seed=sampling.seed,
                    stop=list(sampling.stop),
                )
                for chunk in chunks:
                    if self._stop.is_set():
                        self._finish_reason = FinishReason.STOPPED
                        break
                    choice = chunk["choices"][0]
                    piece = choice["delta"].get("content")
                    if piece:
                        yield piece
                    if choice["finish_reason"] is not None:
                        self._finish_reason = FinishReason(choice["finish_reason"])
            except ValueError as exc:
                if "exceed context window" in str(exc):
                    raise ContextOverflowError(str(exc)) from exc
                raise GenerationError(f"{type(exc).__name__}: {exc}") from exc
            except Exception as exc:
                raise GenerationError(f"{type(exc).__name__}: {exc}") from exc
            finally:
                if chunks is not None:
                    chunks.close()
    
    
    def request_stop(self) -> None:
        self._stop.set()


    @property
    def finish_reason(self) -> FinishReason | None:
        return self._finish_reason


if __name__ == "__main__":
    import sys
    import time
    from core.hardware import detect

    sys.stdout.reconfigure(encoding="utf-8")

    model = sys.argv[1] if len(sys.argv) > 1 else "models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    n_ctx = int(sys.argv[2]) if len(sys.argv) > 2 else 2048

    profil = detect()
    params = LoadParams.for_hardware(model, profil, n_ctx=n_ctx)
    print(f"Model:    {params.model_path.name} ({params.model_size_mb} MB)")
    print(f"Backend:  {profil.backend}  n_threads={params.n_threads}  "
          f"n_gpu_layers={params.n_gpu_layers}  n_ctx={params.n_ctx}")

    engine = LlmEngine()
    start = time.perf_counter()
    notices = engine.load(params)
    print(f"Načítaný: za {time.perf_counter() - start:.1f} s")
    for notice in notices:
        print(f"          {notice.log_line()}")
    print(f"Údaje:    n_ctx={engine.n_ctx}  n_ctx_train={engine.n_ctx_train}  "
          f"n_layers={engine.n_layers}  offloadable={engine.n_layers_offloadable}")
    print(f"Tokeny:   'Ahoj svet' -> {engine.tokenize('Ahoj svet')}")

    print("\n--- streaming ---")
    messages = [
        {"role": "system", "content": "Si stručný asistent, odpovedaj po slovensky."},
        {"role": "user", "content": "Ahoj, kto si?"},
    ]
    start, text = time.perf_counter(), ""
    for piece in engine.stream(messages, SamplingParams(max_tokens=200)):
        print(piece, end="", flush=True)
        text += piece
    elapsed = time.perf_counter() - start
    tokens = engine.count_tokens(text)
    print(f"\n\n{tokens} tokenov za {elapsed:.1f} s ({tokens / elapsed:.1f} t/s), "
          f"koniec: {engine.finish_reason}")

    print("\n--- stop po 10 kúskoch ---")
    stream = engine.stream(
        [{"role": "user", "content": "Vymenuj všetky okresy na Slovensku."}],
        SamplingParams(max_tokens=500),
    )
    for i, piece in enumerate(stream, start=1):
        print(piece, end="", flush=True)
        if i == 10:
            engine.request_stop()
    print(f"\nkoniec: {engine.finish_reason}")

    print("\n--- limit max_tokens=5 ---")
    text = "".join(engine.stream(messages, SamplingParams(max_tokens=5)))
    print(f"{text!r}  koniec: {engine.finish_reason}")

    engine.unload()
    print(f"\nUvoľnený: is_loaded={engine.is_loaded}")
