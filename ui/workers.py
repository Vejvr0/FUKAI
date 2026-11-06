from __future__ import annotations
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from core.constants import IMPORT_CHUNK_BYTES
from core.gguf import check_usable, read_meta
from core.context import HistoryItem, build_prompt
from core.llm_engine import FinishReason, LlmEngine
from core.settings import LoadParams, SamplingParams
from core.errors import FukaiError, GenerationError, ModelImportError, ModelLoadError

__all__ = [
    "GenerateRequest",
    "GenerationResult",
    "ImportRequest",
    "ImportWorker",
    "LlmWorker"
]


@dataclass(frozen=True)
class GenerateRequest:
    id: int
    history: list[HistoryItem]
    question: str
    sampling: SamplingParams
    system_prompt: str = ""
    
    
@dataclass(frozen=True)
class GenerationResult:
    text: str
    finish_reason: FinishReason
    counted: dict[int, int] = field(default_factory=dict)
    dropped: list[int] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    first_token_s: float | None = None
    total_s: float = 0.0
    
    
    @property
    def tokens_per_s(self) -> float | None:
        if self.first_token_s is None:
            return None
        seconds = self.total_s - self.first_token_s
        return self.completion_tokens / seconds if seconds > 0 else None


class LlmWorker(QObject):
    loaded = pyqtSignal(object)
    load_failed = pyqtSignal(object)
    token = pyqtSignal(int, str)
    finished = pyqtSignal(int, object)
    failed = pyqtSignal(int, object)
    
    
    def __init__(self, engine: LlmEngine) -> None:
        super().__init__()
        self._engine = engine
        self._cancelled = -1
        
    
    def cancel(self, request_id: int) -> None:
        self._cancelled = request_id
        
    
    @pyqtSlot(object)
    def load(self, params: LoadParams) -> None:
        try:
            notices = self._engine.load(params)
        except FukaiError as exc:
            self.load_failed.emit(exc)
        except Exception as exc:
            self.load_failed.emit(ModelLoadError(f"{type(exc).__name__}: {exc}"))
        else:
            self.loaded.emit(notices)
    
    
    @pyqtSlot(object)
    def generate(self, request: GenerateRequest) -> None:
        try:
            result = self._generate(request)
        except FukaiError as exc:
            self.failed.emit(request.id, exc)
        except Exception as exc:
            self.failed.emit(request.id, GenerationError(f"{type(exc).__name__}: {exc}"))
        else:
            self.finished.emit(request.id, result)
    
    
    def _generate(self, request: GenerateRequest) -> GenerationResult:
        engine = self._engine
        started = time.monotonic()
        n_ctx = engine.n_ctx
        
        if n_ctx is None:
            raise ModelLoadError("generovanie bez načítaného modelu")
        plan = build_prompt(
            request.history,
            request.question,
            system_prompt=request.system_prompt,
            n_ctx=n_ctx,
            max_tokens=request.sampling.max_tokens,
            count=engine.count_tokens
        )
        done = dict(counted=plan.counted, dropped=plan.dropped, prompt_tokens=plan.prompt_tokens)
        
        if self._cancelled == request.id:
            return GenerationResult("", FinishReason.STOPPED, total_s=time.monotonic() - started, **done)
        
        parts: list[str] = []
        first_token_s = None
        for piece in engine.stream(plan.messages, request.sampling):
            if self._cancelled == request.id:
                engine.request_stop()
            if first_token_s is None:
                first_token_s = time.monotonic() - started
            parts.append(piece)
            self.token.emit(request.id, piece)
        text = "".join(parts)
        reason = engine.finish_reason
        
        if reason is None:
            raise GenerationError("generovanie skončilo bez finish_reason")
        
        return GenerationResult(
            text,
            reason,
            completion_tokens=engine.count_tokens(text) if text else 0,
            first_token_s=first_token_s,
            total_s=time.monotonic() - started,
            **done
        )


@dataclass(frozen=True)
class ImportRequest:
    source: Path
    dest: Path
    cancel: threading.Event


class ImportWorker(QObject):
    progress = pyqtSignal("qint64", "qint64")
    finished = pyqtSignal(object, object)
    failed = pyqtSignal(object)
    cancelled = pyqtSignal()
    
    
    @pyqtSlot(object)
    def run(self, request: ImportRequest) -> None:
        try:
            meta = read_meta(request.source)
            check_usable(meta)
            done = self._copy(request)
        except FukaiError as exc:
            self.failed.emit(exc)
        except Exception as exc:
            self.failed.emit(ModelImportError(f"{type(exc).__name__}: {exc}"))
        else:
            if done:
                self.finished.emit(request.dest, meta)
            else:
                self.cancelled.emit()
    
    
    def _copy(self, request: ImportRequest) -> bool:
        part = request.dest.with_name(request.dest.name + ".part")
        total = request.source.stat().st_size
        cancelled = False
        try:
            with request.source.open("rb") as src, part.open("wb") as dst:
                copied = 0
                while chunk := src.read(IMPORT_CHUNK_BYTES):
                    if request.cancel.is_set():
                        cancelled = True
                        break
                    dst.write(chunk)
                    copied += len(chunk)
                    self.progress.emit(copied, total)
                else:
                    dst.flush()
                    os.fsync(dst.fileno())
            if cancelled or request.cancel.is_set():
                part.unlink(missing_ok=True)
                return False
            os.replace(part, request.dest)
        except OSError as exc:
            part.unlink(missing_ok=True)
            raise ModelImportError(
                f"{type(exc).__name__}: {exc}",
                message="Kopírovanie modelu do knižnice zlyhalo."
            ) from exc
        return True
