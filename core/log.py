from __future__ import annotations
import faulthandler
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from core.constants import LOG_BACKUPS, LOG_MAX_BYTES, LOG_FORMAT, OWN_PACKAGES
from core.paths import crash_log_path, logs_path, ensure_dir

__all__ = ["setup_logging", "enable_crash_log"]

_crash_file = None      # faulthandler potrebuje otvorený súbor po celý beh procesu


def setup_logging(path: Path | None = None) -> Path | None:
    path = path or logs_path()
    try:
        ensure_dir(path.parent)
        handler = RotatingFileHandler(path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUPS, encoding="utf-8")
    except OSError:
        return None
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.WARNING)
    for name in OWN_PACKAGES:
        logging.getLogger(name).setLevel(logging.INFO)
    return path


def enable_crash_log(path: Path | None = None) -> Path | None:
    """Tvrdý pád v C kóde (llama.cpp, Metal, CUDA, Qt) Python nezachytí a fukai.log o ňom
    nič nepovie. faulthandler pri ňom zapíše traceback všetkých vlákien do samostatného súboru -
    nie do fukai.log, ten pri rotácii mení meno. Nikdy nevyhodí výnimku."""
    global _crash_file
    path = path or crash_log_path()
    try:
        ensure_dir(path.parent)
        _crash_file = open(path, "a", encoding="utf-8")
        faulthandler.enable(file=_crash_file, all_threads=True)
    except (OSError, RuntimeError):
        return None
    return path
