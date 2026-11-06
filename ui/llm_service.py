from __future__ import annotations
import itertools
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from core.context import HistoryItem
from core.llm_engine import LlmEngine
from core.settings import LoadParams, SamplingParams
from core.errors import FukaiError, Notice
from ui.workers import GenerateRequest, GenerationResult, LlmWorker

__all__ = ["LlmService"]


class LlmService(QObject):
    _load_requested = pyqtSignal(object)
    _generate_requested = pyqtSignal(object)
    
    loaded = pyqtSignal(object)
    load_failed = pyqtSignal(object)
    token = pyqtSignal(int, str)
    finished = pyqtSignal(int, object)
    failed = pyqtSignal(int, object)
    busy_changed = pyqtSignal(bool)
    
    
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._engine = LlmEngine()
        self._ids = itertools.count(1)
        self._busy = False
        self._current: int | None = None
        
        self._thread = QThread()
        self._thread.setObjectName("llm")
        self._worker = LlmWorker(self._engine)
        self._worker.moveToThread(self._thread)
        
        self._load_requested.connect(self._worker.load)
        self._generate_requested.connect(self._worker.generate)
        self._worker.loaded.connect(self._on_loaded)
        self._worker.load_failed.connect(self._on_load_failed)
        self._worker.token.connect(self.token)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        
        self._thread.start()
        
    
    @property
    def busy(self) -> bool:
        return self._busy
    
    
    @property
    def current_request(self) -> int | None:
        return self._current
    
    
    @property
    def engine(self) -> LlmEngine:
        return self._engine
    
    
    def _set_busy(self, busy: bool) -> None:
        if busy != self._busy:
            self._busy = busy
            self.busy_changed.emit(busy)
    
    
    def _require_idle(self) -> None:
        if self._busy:
            raise RuntimeError("LLM služba je zaneprázdnená - počkaj kým spracuje úlohu.")
    
    
    def load(self, params: LoadParams) -> None:
        self._require_idle()
        self._set_busy(True)
        self._load_requested.emit(params)
    
    
    def unload(self) -> None:
        self._require_idle()
        self._engine.unload()
    
    
    def generate(self, history: list[HistoryItem], question: str, *, sampling: SamplingParams, system_prompt: str = "") -> int:
        self._require_idle()
        request = GenerateRequest(next(self._ids), history, question, sampling, system_prompt)
        self._current = request.id
        self._set_busy(True)
        self._generate_requested.emit(request)
        return request.id
    
    
    def stop(self) -> None:
        if self._current is not None:
            self._worker.cancel(self._current)
            self._engine.request_stop()
    
    
    def shutdown(self) -> None:
        if not self._thread.isRunning():
            return
        self.stop()
        self._thread.quit()
        self._thread.wait()
        self.engine.unload()
    
    
    def _on_loaded(self, notices: list[Notice]) -> None:
        self._set_busy(False)
        self.loaded.emit(notices)
        
    
    def _on_load_failed(self, error: FukaiError) -> None:
        self._set_busy(False)
        self.load_failed.emit(error)
        
    
    def _on_finished(self, request_id: int, result: GenerationResult) -> None:
        self._current = None
        self._set_busy(False)
        self.finished.emit(request_id, result)
    
    
    def _on_failed(self, request_id: int, error: FukaiError) -> None:
        self._current = None
        self._set_busy(False)
        self.failed.emit(request_id, error)