from __future__ import annotations
import threading
from types import ModuleType
from core.settings import LoadParams
from core.errors import BackendUnavailableError, ModelLoadError

__all__ = ["LlmEngine"]


def _import_llama() -> ModuleType:
    try:
        import llama_cpp
    except (ImportError, OSError) as exc:
        raise BackendUnavailableError(f"{type(exc).__name__}: {exc}") from exc
    return llama_cpp


class LlmEngine:
    def __init__(self, *, verbose: bool = False) -> None:
        self.verbose = verbose
        self._llm = None
        self._params: LoadParams | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        
        
    @property
    def is_loaded(self) -> bool:
        return self._llm is not None
    
    
    def _require_loaded(self):
        if self._llm is None:
            raise ModelLoadError("model nie je načítaný, najprv treba načítať model")
        return self._llm
    
    
    def load(self, params: LoadParams) -> None:
        params = params.clamped()
        params.validate()
        llama = _import_llama()
        
        with self._lock:
            self._unload_locked()
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
                raise ModelLoadError(f"{type(exc).__name__}: {exc}") from exc
            self._llm = llm
            self._params = params
    
    
    def unload(self) -> None:
        with self._lock:
            self._unload_locked()
    
    
    def _unload_locked(self) -> None:
        llm, self._llm, self._params = self._llm, None, None
        if llm is not None:
            llm.close()