from __future__ import annotations
import itertools
import threading
from typing import Callable
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from ui.workers import WebRequest, WebWorker

__all__ = ["WebService"]


class WebService(QObject):
    _requested = pyqtSignal(object)
    progress = pyqtSignal(int, str)
    ready = pyqtSignal(int, object)
    failed = pyqtSignal(int, object)
    
    
    def __init__(self, parent: QObject | None = None, *, gather: Callable[..., list] | None = None) -> None:
        super().__init__(parent)
        self._ids = itertools.count(1)
        self._cancels: dict[int, threading.Event] = {}
        
        self._thread = QThread()
        self._thread.setObjectName("web")
        self._worker = WebWorker(gather) if gather is not None else WebWorker()
        self._worker.moveToThread(self._thread)
        
        self._requested.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.ready.connect(self._on_ready)
        self._worker.failed.connect(self._on_failed)
        self._thread.start()
        
        
    def search(self, query: str) -> int:
        job_id = next(self._ids)
        cancel = threading.Event()
        self._cancels[job_id] = cancel
        self._requested.emit(WebRequest(job_id, query, cancel))
        return job_id
    
    
    def cancel(self, job_id: int) -> None:
        event = self._cancels.pop(job_id, None)
        if event is not None:
            event.set()
    
    
    def shutdown(self) -> None:
        for event in self._cancels.values():
            event.set()
        self._cancels.clear()
        if self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
    
    
    def _on_progress(self, job_id: int, text: str) -> None:
        if job_id in self._cancels:
            self.progress.emit(job_id, text)
    
    
    def _on_ready(self, job_id: int, sources: list) -> None:
        if self._cancels.pop(job_id, None) is not None:
            self.ready.emit(job_id, sources)
    
    
    def _on_failed(self, job_id: int, error) -> None:
        if self._cancels.pop(job_id, None) is not None:
            self.failed.emit(job_id, error)
