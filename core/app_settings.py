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

__all__ = ["AppSettings", "load_settings", "save_settings"]


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


if __name__ == "__main__":
    import shutil
    import sys
    from core.paths import app_dir

    sys.stdout.reconfigure(encoding="utf-8")

    home = Path(__file__).resolve().parent.parent / "devdata" / "selftest-settings"
    shutil.rmtree(home, ignore_errors=True)
    home.mkdir(parents=True)
    os.environ["FUKAI_HOME"] = str(home)      # §7.1: inak by test zapisoval do AppData
    path = settings_path()
    print(f"FUKAI_HOME:   {app_dir()}")
    print(f"settings.json {path}")

    print("\n--- predvolené hodnoty ---")
    for key, value in AppSettings().to_dict().items():
        print(f"{key + ':':<22}{value!r}")

    print("\n--- prvé spustenie (súbor neexistuje) ---")
    settings, notices = load_settings(path)
    print(f"notices:      {[n.log_line() for n in notices]}")
    print(f"súbor vznikol:{path.is_file()}  priečinok modelov: {settings.models_dir.is_dir()}")
    print(f"obsah:        {json.loads(path.read_text(encoding='utf-8'))}")

    print("\n--- round-trip cez súbor ---")
    changed = replace(settings, theme="dark", attachments_enabled=False, last_model_id=7)
    save_settings(changed, path)
    back, notices = load_settings(path)
    print(f"rovnaké:      {back == changed}  notices: {len(notices)}")
    print(f"téma:         {back.theme}  prílohy: {back.attachments_enabled}  model: {back.last_model_id}")
    print(f"zostal .tmp?  {[p.name for p in home.glob('*.tmp')] or 'nie'}")

    print("\n--- pečiatka verzie ---")
    save_settings(replace(changed, version=99), path)
    print(f"zapísaná verzia 99 → v súbore "
          f"{json.loads(path.read_text(encoding='utf-8'))['version']} (SETTINGS_VERSION)")

    print("\n--- rozbitý súbor ---")
    path.write_text("{toto nie je json", encoding="utf-8")
    settings, notices = load_settings(path)
    print(f"téma:         {settings.theme} (predvolená)")
    print(f"notice:       {notices[0].log_line() if notices else 'ŽIADNY!'}")
    print(f"prepísaný:    {json.loads(path.read_text(encoding='utf-8'))['theme']!r} je už platný JSON")

    print("\n--- JSON, ktorý nie je objekt ---")
    path.write_text("[1, 2, 3]", encoding="utf-8")
    settings, notices = load_settings(path)
    print(f"notice:       {notices[0].detail if notices else 'ŽIADNY!'}")

    print("\n--- blob z inej verzie appky ---")
    path.write_text(json.dumps({
        "theme": "sepia",                    # neznáma téma
        "models_dir": None,                  # null, nie chýbajúci kľúč
        "neznamy_kluc": 1,                   # kľúč navyše
        "last_model_id": 3,                  # web_search_enabled chýba
    }), encoding="utf-8")
    settings, notices = load_settings(path)
    print(f"téma sepia →  {settings.theme!r}")
    print(f"models_dir:   {settings.models_dir} (null → predvolený)")
    print(f"chýbajúci:    web_search_enabled={settings.web_search_enabled}")
    print(f"navyše:       zahodený, model={settings.last_model_id}")

    print("\n--- nedostupný priečinok modelov ---")
    blocker = home / "blocker"
    blocker.write_text("nie som priečinok", encoding="utf-8")
    path.write_text(json.dumps({"models_dir": str(blocker / "models")}), encoding="utf-8")
    settings, notices = load_settings(path)
    print(f"notice:       {notices[0].message if notices else 'ŽIADNY!'}")
    print(f"fallback:     {settings.models_dir}")

    print("\n--- zápis, ktorý sa nedá vykonať ---")
    try:
        save_settings(AppSettings(), blocker / "settings.json")
        print("              ULOŽILO SA?!")
    except ConfigError as exc:
        print(f"ConfigError:  {exc.message}")
        print(f"detail:       {exc}")
        print(f"zostal .tmp?  {[p.name for p in blocker.parent.glob('*.tmp')] or 'nie'}")