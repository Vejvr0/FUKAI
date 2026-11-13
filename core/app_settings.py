# --- ./core/app_settings.py ---


from __future__ import annotations
from dataclasses import dataclass, field, replace
from pathlib import Path
import json
import os
from core.paths import default_models_dir, settings_path, ensure_dir
from core.errors import Notice, ConfigError
from core.constants import (
    SETTINGS_VERSION, THEMES, THEME_DEFAULT,
    ATTACHMENTS_ENABLED_DEFAULT, WEB_SEARCH_ENABLED_DEFAULT
)

__all__ = [
    "AppSettings",
    "load_settings",
    "save_settings"
]


@dataclass(frozen=True)
class AppSettings:
    models_dir: Path = field(default_factory=default_models_dir)
    theme: str = THEME_DEFAULT
    attachments_enabled: bool = ATTACHMENTS_ENABLED_DEFAULT
    web_search_enabled: bool = WEB_SEARCH_ENABLED_DEFAULT
    last_model_id: int | None = None
    version: int = SETTINGS_VERSION


    def __post_init__(self) -> None:
        object.__setattr__(self, "models_dir", Path(self.models_dir).expanduser().resolve())


    def to_dict(self) -> dict:
        return {
            "models_dir": str(self.models_dir),
            "theme": self.theme,
            "attachments_enabled": self.attachments_enabled,
            "web_search_enabled": self.web_search_enabled,
            "last_model_id": self.last_model_id,
            "version": self.version
        }


    @classmethod
    def from_dict(cls, data: dict) -> AppSettings:
        theme = data.get("theme")
        return cls(
            models_dir=data.get("models_dir") or default_models_dir(),
            theme=theme if theme in THEMES else THEME_DEFAULT,
            attachments_enabled=data.get("attachments_enabled", ATTACHMENTS_ENABLED_DEFAULT),
            web_search_enabled=data.get("web_search_enabled", WEB_SEARCH_ENABLED_DEFAULT),
            last_model_id=data.get("last_model_id"),
            version=data.get("version", SETTINGS_VERSION)
        )


def load_settings(path: Path | None = None) -> tuple[AppSettings, list[Notice]]:
    path = Path(path) if path else settings_path()
    notice: list[Notice] = []
    settings = AppSettings()
    write_defaults = True

    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"očakávaný objekt, prišlo {type(data).__name__}")
            settings = AppSettings.from_dict(data)
            write_defaults = False
        except (OSError, ValueError) as exc:
            notice.append(Notice.warning(
                "Nastavenia aplikácie boli poškodené, obnovili sa predvolené.",
                hint="Nastavenia aplikácie si nastav znova.",
                detail=f"{type(exc).__name__}: {exc} ({path})"
            ))

    if write_defaults:
        try:
            save_settings(settings, path)
        except ConfigError as exc:
            notice.append(exc.as_notice())

    try:
        ensure_dir(settings.models_dir)
    except OSError as exc:
        notice.append(Notice.warning(
            f"Adresár s modelmi {settings.models_dir} nie je dostupný, používa sa predvolený.",
            hint="Skontroluj, či je disk pripojený a máš oprávnenie zapisovať do adresára.",
            detail=f"{type(exc).__name__}: {exc}"
        ))
        settings = replace(settings, models_dir=default_models_dir())

    return settings, notice


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    path = Path(path) if path else settings_path()
    tmp = path.with_name(path.name + ".tmp")
    stamped = replace(settings, version=SETTINGS_VERSION)
    try:
        ensure_dir(path.parent)
        tmp.write_text(json.dumps(stamped.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise ConfigError(
            f"{type(exc).__name__}: {exc} ({path})",
            message="Nastavenia aplikácie sa nepodarilo uložiť.",
            hint="Skontroluj miesto na disku a práva na zápis do adresára."
        ) from exc
