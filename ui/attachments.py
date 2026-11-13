# --- attachments.py ---


from __future__ import annotations
import itertools
from pathlib import Path
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from ui.workers import ExtractRequest, ExtractWorker

__all__ = ["AttachmentService"]


class AttachmentService(QObject):
    _requested = pyqtSignal(object)
    ready = pyqtSignal(int, object)
    failed = pyqtSignal(int, object)


    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ids = itertools.count(1)

        self._thread = QThread()
        self._thread.setObjectName("attachments")
        self._worker = ExtractWorker()
        self._worker.moveToThread(self._thread)

        self._requested.connect(self._worker.run)
        self._worker.ready.connect(self.ready)
        self._worker.failed.connect(self.failed)
        self._thread.start()


    def extract(self, path: str | Path) -> int:
        job_id = next(self._ids)
        self._requested.emit(ExtractRequest(job_id, Path(path)))
        return job_id


    def shutdown(self) -> None:
        if self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
