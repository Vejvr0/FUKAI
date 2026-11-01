from __future__ import annotations
import os
import platformdirs
from pathlib import Path
from core.constants import APP_NAME, SETTINGS_FILENAME, DB_FILENAME, MODELS_DIRNAME

__all__ = [
    "APP_NAME",
    "app_dir",
    "settings_path",
    "db_path",
    "default_models_dir",
    "ensure_dir",
]


def app_dir() -> Path:
    home = os.environ.get("FUKAI_HOME")
    if home:
        return Path(home).expanduser().resolve()
    return Path(platformdirs.user_data_dir(APP_NAME, appauthor=False))


def settings_path() -> Path:
    return app_dir() / SETTINGS_FILENAME


def db_path() -> Path:
    return app_dir() / DB_FILENAME


def default_models_dir() -> Path:
    return app_dir() / MODELS_DIRNAME


def ensure_dir(path: str | Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    print(f"app_dir            {app_dir()}")
    print(f"settings_path      {settings_path()}")
    print(f"db_path            {db_path()}")
    print(f"default_models_dir {default_models_dir()}")
    print(f"\nexistuje už app_dir? {app_dir().exists()}")
