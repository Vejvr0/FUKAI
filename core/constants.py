from pathlib import Path

APP_NAME = "FUKAI"
SETTINGS_FILENAME = "settings.json"
DB_FILENAME = "fukai.db"
MODELS_DIRNAME = "models"
HW_CONF = Path(__file__).resolve().parent.parent / "vars" / "hw.json"
RELATION_PROCESSOR_CORE = 0
ERROR_INSUFFICIENT_BUFFER = 122