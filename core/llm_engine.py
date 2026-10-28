from __future__ import annotations

import threading
from collections.abc import Iterable, Iterator
from types import ModuleType

import psutil

from core.errors import (
    BackendUnavailableError,
    FukaiError,
    GenerationError,
    InsufficientMemoryError,
    ModelLoadError,
    Notice,
)
from core.settings import LoadParams, SamplingParams

__all__ = ["LlmEngine"]

# Podľa týchto slov v texte chyby z llama.cpp sa zlyhanie načítania
# vyhodnotí ako nedostatok pamäte, nie ako poškodený model.
_MEMORY_WORDS = ("out of memory", "alloc", "oom", "not enough", "cudamalloc")


def _import_llama() -> ModuleType:
    """Import `llama_cpp` až keď je naozaj treba.

    Import trvá dlho (načítava `llama.dll`, pri CUDA builde inicializuje GPU)
    a na stroji bez správneho wheelu zlyhá. Preto nie je na úrovni modulu –
    appka sa musí dať spustiť aj vtedy, keď engine chýba, a chybu ukázať v UI.
    """
    try:
        import llama_cpp
    except (ImportError, OSError) as exc:
        raise BackendUnavailableError(f"{type(exc).__name__}: {exc}") from exc
    return llama_cpp


def _free_ram_mb() -> int:
    """Voľná RAM teraz.

    Zámerne sa nepoužíva `ram_available_mb` z `HardwareProfile` – ten sa meria
    raz pri štarte aplikácie a do načítania modelu je už neplatný (ALMANAC §4).
    """
    return psutil.virtual_memory().available // 1024 // 1024


class LlmEngine:
    """Načítanie `.gguf` modelu, streamované generovanie a zastavenie.

    Model sa **nenačítava v konštruktore** – až v `load()`, a dá sa reloadnúť
    (ALMANAC §5, bod 2). Trieda je navrhnutá na použitie z QThread workera:
    `load()` a `stream()` bežia vo worker vlákne, `request_stop()` sa smie volať
    z UI vlákna, lebo len nastaví `threading.Event`.
    """

    def __init__(self, *, verbose: bool = False) -> None:
        self.verbose = verbose
        self._llm = None
        self._params: LoadParams | None = None
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._generating = False
        self._stopped = False

    # --- stav ---------------------------------------------------------------

    @property
    def is_loaded(self) -> bool:
        return self._llm is not None

    @property
    def params(self) -> LoadParams | None:
        """Parametre, s ktorými je model práve načítaný."""
        return self._params

    @property
    def is_generating(self) -> bool:
        return self._generating

    @property
    def stopped(self) -> bool:
        """True, keď posledné generovanie skončilo na žiadosť používateľa."""
        return self._stopped

    @property
    def n_layers(self) -> int | None:
        """Počet blokov modelu z metadát `.gguf`, nie z ručného zoznamu.

        Prototyp mal počet vrstiev prepísaný v JSON-e (ALMANAC §5, bod 3).
        """
        if self._llm is None:
            return None
        llama = _import_llama()
        return int(llama.llama_model_n_layer(self._llm._model.model))

    @property
    def n_layers_offloadable(self) -> int | None:
        """Maximum pre `n_gpu_layers` – bloky + výstupná vrstva.

        llama.cpp hlási „offloaded 35/35“ pri 34 blokoch, posledná vrstva je
        výstupná. Toto číslo je horná hranica slidera CPU/GPU.
        """
        layers = self.n_layers
        return None if layers is None else layers + 1

    @property
    def n_ctx_train(self) -> int | None:
        """Dĺžka kontextu, na ktorú bol model trénovaný."""
        if self._llm is None:
            return None
        llama = _import_llama()
        return int(llama.llama_model_n_ctx_train(self._llm._model.model))

    @property
    def n_ctx(self) -> int | None:
        """Skutočná dĺžka kontextu načítaného modelu."""
        return None if self._llm is None else int(self._llm.n_ctx())

    # --- načítanie ----------------------------------------------------------

    def load(self, params: LoadParams, *, force: bool = False) -> list[Notice]:
        """Načíta model. Vracia nefatálne oznámenia, chyby vyhadzuje.

        Keď je ten istý model už načítaný s rovnakými parametrami, nerobí nič –
        `force=True` ho reloadne aj tak.
        """
        params = params.clamped()
        params.validate()
        llama = _import_llama()

        with self._lock:
            if self._llm is not None and not force and params == self._params:
                return []

            self._unload_locked()
            notices = self._memory_notices(params)

            try:
                llm = llama.Llama(
                    model_path=str(params.model_path),
                    n_ctx=params.n_ctx,
                    n_gpu_layers=params.n_gpu_layers,
                    n_threads=params.n_threads,
                    n_batch=params.n_batch,
                    use_mmap=params.use_mmap,
                    verbose=self.verbose,
                )
            except FukaiError:
                raise
            except Exception as exc:
                detail = f"{type(exc).__name__}: {exc}"
                if any(word in str(exc).lower() for word in _MEMORY_WORDS):
                    raise InsufficientMemoryError(
                        detail,
                        needed_mb=params.model_size_mb,
                        available_mb=_free_ram_mb(),
                    ) from exc
                raise ModelLoadError(detail) from exc

            self._llm = llm
            self._params = params

            trained = self.n_ctx_train
            if trained and params.n_ctx > trained:
                notices.append(Notice.warning(
                    f"Nastavená dĺžka kontextu je väčšia, než na akú bol model trénovaný "
                    f"({params.n_ctx} oproti {trained} tokenom).",
                    hint="Model môže na dlhom kontexte odpovedať nespoľahlivo.",
                ))
            return notices

    def ensure_loaded(self, params: LoadParams) -> list[Notice]:
        """Načíta model, len keď ešte nebeží alebo sa zmenili load parametre."""
        return self.load(params)

    def unload(self) -> None:
        with self._lock:
            self._unload_locked()

    def _unload_locked(self) -> None:
        llm, self._llm, self._params = self._llm, None, None
        if llm is not None:
            try:
                llm.close()
            except Exception:
                pass    # uvolnenie pamäte nesmie zhodiť appku

    def _memory_notices(self, params: LoadParams) -> list[Notice]:
        """Orientačné porovnanie veľkosti `.gguf` s voľnou pamäťou.

        Samostatný „rozpočet pamäte“ sa zámerne nerobí (ALMANAC §4) – presný
        odhad KV cache sem nepatrí, stačí varovať. Ak sa model aj tak nenačíta,
        skutočnú chybu nahlási llama.cpp a `load()` ju preloží na
        `InsufficientMemoryError`.
        """
        size_mb = params.model_size_mb
        if size_mb == 0:
            return []

        free_mb = _free_ram_mb()
        if params.on_gpu or free_mb >= size_mb * 1.2:
            return []

        return [Notice.warning(
            f"Model má {size_mb / 1024:.1f} GB a voľnej pamäte je {free_mb / 1024:.1f} GB – "
            f"načítanie môže zlyhať alebo byť veľmi pomalé.",
            hint="Zatvor iné aplikácie, zvoľ menší model, alebo zníž dĺžku kontextu.",
            detail=f"model {size_mb} MB, volna RAM {free_mb} MB, n_gpu_layers={params.n_gpu_layers}",
        )]

    # --- tokeny -------------------------------------------------------------

    def tokenize(self, text: str) -> list[int]:
        """Tokenizácia načítaným modelom – pre orezávanie histórie v `context.py`."""
        llm = self._require_loaded()
        return llm.tokenize(text.encode("utf-8"), add_bos=False, special=False)

    def count_tokens(self, text: str) -> int:
        return len(self.tokenize(text))

    # --- generovanie --------------------------------------------------------

    def request_stop(self) -> None:
        """Požiada o zastavenie generovania. Volateľné z UI vlákna."""
        self._stop.set()

    def stream(
        self,
        messages: Iterable[dict],
        sampling: SamplingParams | None = None,
    ) -> Iterator[str]:
        """Generuje odpoveď po častiach.

        Chat template sa berie z metadát `.gguf` cez `create_chat_completion()`,
        prompt sa neskladá ručne (ALMANAC §7). Pri zastavení generátor skončí
        normálne a `stopped` je True – doteraz vygenerovaný text je platný
        výstup, nie chyba.
        """
        sampling = (sampling or SamplingParams()).clamped()
        llm = self._require_loaded()

        self._stop.clear()
        self._stopped = False
        self._generating = True
        chunks = None

        try:
            chunks = llm.create_chat_completion(
                messages=list(messages),
                stream=True,
                temperature=sampling.temperature,
                top_p=sampling.top_p,
                top_k=sampling.top_k,
                repeat_penalty=sampling.repeat_penalty,
                max_tokens=sampling.max_tokens,
                stop=list(sampling.stop),
                **({"seed": sampling.seed} if sampling.seed is not None else {}),
            )
            for chunk in chunks:
                if self._stop.is_set():
                    self._stopped = True
                    break
                piece = chunk["choices"][0].get("delta", {}).get("content")
                if piece:
                    yield piece
        except FukaiError:
            raise
        except Exception as exc:
            raise GenerationError(f"{type(exc).__name__}: {exc}") from exc
        finally:
            self._generating = False
            if chunks is not None:
                chunks.close()      # uvolní sampler v llama.cpp

    def _require_loaded(self):
        llm = self._llm
        if llm is None:
            raise ModelLoadError("model nie je načítaný, zavolaj load() najprv")
        return llm


if __name__ == "__main__":
    # Konzolový test podľa ALMANAC §8, krok 3: load .gguf, streaming, stop.
    import sys
    import time

    sys.stdout.reconfigure(encoding="utf-8")

    from core import hardware

    model = sys.argv[1] if len(sys.argv) > 1 else "models/gemma-3-4b-it-Q4_K_M.gguf"

    profil = hardware.detect()
    params = LoadParams.for_hardware(model, profil, n_ctx=2048)
    print(f"backend={profil.backend}  n_threads={params.n_threads}  "
          f"n_gpu_layers={params.n_gpu_layers}  n_ctx={params.n_ctx}")

    engine = LlmEngine()
    start = time.perf_counter()
    for notice in engine.load(params):
        print("  ", notice.log_line())
    print(f"model načítaný za {time.perf_counter() - start:.1f} s  "
          f"(vrstvy {engine.n_layers}, offload max {engine.n_layers_offloadable}, "
          f"trénované na {engine.n_ctx_train} tokenov)")

    messages = [
        {"role": "system", "content": "Si užitočný a stručný asistent, odpovedaj po slovensky."},
        {"role": "user", "content": "Ahoj, kto si?"},
    ]

    print("\n--- streaming ---")
    start, tokens = time.perf_counter(), 0
    for piece in engine.stream(messages, SamplingParams(max_tokens=200)):
        print(piece, end="", flush=True)
        tokens += 1
    elapsed = time.perf_counter() - start
    print(f"\n\n{tokens} častí za {elapsed:.1f} s  ({tokens / elapsed:.1f}/s)")

    print("\n--- test stop po 10 častiach ---")
    stream = engine.stream(
        [{"role": "user", "content": "Vymenuj po jednom všetky okresy na Slovensku."}],
        SamplingParams(max_tokens=500),
    )
    for i, piece in enumerate(stream, start=1):
        print(piece, end="", flush=True)
        if i == 10:
            engine.request_stop()
    print(f"\n\nstopped={engine.stopped}  is_generating={engine.is_generating}")

    engine.unload()
    print(f"unload hotový, is_loaded={engine.is_loaded}")
