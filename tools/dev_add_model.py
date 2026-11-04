r"""DOČASNÉ – len pre vývoj, kým nie je import modelu (krok 10–11).

Zaregistruje .gguf do tabuľky `models` a nastaví ho ako posledný použitý:
    FUKAI_HOME=./devdata python -m tools.dev_add_model /cesta/k/modelu.gguf
    (PowerShell: $env:FUKAI_HOME = ".\devdata"; python -m tools.dev_add_model C:\...\model.gguf)

Model sa nekopíruje – do `models_dir` sa vytvorí symlink, `models.path` je relatívny názov
(tak ako bude pri importe, §7.1). Opakované spustenie s tým istým súborom nič nepridá.
"""
import sys
from dataclasses import replace
from pathlib import Path
from core.app_settings import load_settings, save_settings
from storage.database import Database

source = Path(sys.argv[1]).expanduser().resolve()
if not source.is_file():
    raise SystemExit(f"súbor neexistuje: {source}")

settings, _ = load_settings()
link = settings.models_dir / source.name
if not link.exists():
    try:
        link.symlink_to(source)
    except OSError:                     # Windows: symlink chce admina / vývojársky režim
        link.hardlink_to(source)        # hard link funguje bez práv, ale len na tom istom disku

with Database() as db:
    existing = [m for m in db.list_models() if m["path"] == source.name]
    model_id = existing[0]["id"] if existing else db.add_model(source.stem, source.name)

save_settings(replace(settings, last_model_id=model_id))
print(f"model id={model_id}  {source.stem}  →  {link}")
