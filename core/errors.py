from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "Severity",
    "Notice",
    "FukaiError",
    "ConfigError",
    "HardwareError",
    "GpuProbeError",
    "ModelError",
    "ModelNotFoundError",
    "ModelFormatError",
    "ModelImportError",
    "BackendUnavailableError",
    "ModelLoadError",
    "InsufficientMemoryError",
    "GenerationError",
    "ContextOverflowError",
    "StorageError",
    "DatabaseCorruptError",
    "AttachmentError",
    "UnsupportedAttachmentError",
    "AttachmentTooLargeError",
    "AttachmentParseError",
    "WebSearchError",
]


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Notice:
    severity: Severity
    message: str
    hint: str | None = None
    detail: str | None = None

    @classmethod
    def info(cls, message: str, *, hint: str | None = None, detail: str | None = None) -> Notice:
        return cls(Severity.INFO, message, hint, detail)

    @classmethod
    def warning(cls, message: str, *, hint: str | None = None, detail: str | None = None) -> Notice:
        return cls(Severity.WARNING, message, hint, detail)

    @classmethod
    def error(cls, message: str, *, hint: str | None = None, detail: str | None = None) -> Notice:
        return cls(Severity.ERROR, message, hint, detail)

    def text(self) -> str:
        return f"{self.message}\n\n{self.hint}" if self.hint else self.message

    def log_line(self) -> str:
        line = f"[{self.severity.value.upper()}] {self.message}"
        return f"{line} | {self.detail}" if self.detail else line


class FukaiError(Exception):
    default_message = "Nastala neočakávaná chyba aplikácie."
    default_hint: str | None = None
    severity = Severity.ERROR

    def __init__(
        self,
        detail: str = "",
        *,
        message: str | None = None,
        hint: str | None = None,
    ) -> None:
        self.detail = detail
        self.message = message or self.default_message
        self.hint = hint if hint is not None else self.default_hint
        super().__init__(detail or self.message)

    def __str__(self) -> str:
        return self.detail or self.message

    def text(self) -> str:
        return self.as_notice().text()

    def as_notice(self) -> Notice:
        return Notice(self.severity, self.message, self.hint, self.detail or None)


# --- Nastavenia ------------------------------------------------------------


class ConfigError(FukaiError):
    default_message = "Nastavenia aplikácie sa nepodarilo načítať."
    default_hint = "Skús obnoviť predvolené nastavenia."


# --- Hardvér ---------------------------------------------------------------


class HardwareError(FukaiError):
    default_message = "Parametre tvojho hardvéru sa nepodarilo zistiť."


class GpuProbeError(HardwareError):
    default_message = "Grafickú kartu sa nepodarilo detekovať."
    default_hint = "Model pobeží na procesore. Skontroluj ovládače grafickej karty."


# --- Model -----------------------------------------------------------------


class ModelError(FukaiError):
    default_message = "Nastala chyba pri práci s modelom."


class ModelNotFoundError(ModelError):
    default_message = "Model sa nenašiel."
    default_hint = "Skontroluj cestu k modelu v nastaveniach."


class ModelFormatError(ModelError):
    default_message = "Vložený model nemá podporovaný formát."
    default_hint = "FUKAI podporuje iba modely s príponou .gguf."


class ModelImportError(ModelError):
    default_message = "Model sa nepodarilo importovať."
    default_hint = "Skontroluj voľné miesto na disku a prístup k priečinku modelov."


class BackendUnavailableError(ModelError):
    default_message = "Engine pre spúšťanie modelov nie je dostupný."
    default_hint = "Nainštaluj llama-cpp-python podľa requirements-llama-*.txt."


class ModelLoadError(ModelError):
    default_message = "Model sa nepodarilo načítať."
    default_hint = "Skús menší model, alebo zníž dĺžku kontextu."


class InsufficientMemoryError(ModelError):
    default_message = "Na načítanie modelu nie je dosť operačnej pamäte."
    default_hint = "Zvoľ menší model, zníž dĺžku kontextu, alebo uber vrstvy na GPU."

    def __init__(
        self,
        detail: str = "",
        *,
        needed_mb: float | None = None,
        available_mb: float | None = None,
        where: str = "pamäti",
        message: str | None = None,
        hint: str | None = None,
    ) -> None:
        self.needed_mb = needed_mb
        self.available_mb = available_mb
        if message is None and needed_mb is not None and available_mb is not None:
            message = (
                f"Na načítanie modelu nie je dosť {where}: "
                f"potrebných je približne {needed_mb / 1024:.1f} GB, "
                f"dostupných {available_mb / 1024:.1f} GB."
            )
        super().__init__(detail, message=message, hint=hint)


# --- Generovanie -----------------------------------------------------------


class GenerationError(FukaiError):
    default_message = "Odpoveď sa nepodarilo vygenerovať."


class ContextOverflowError(GenerationError):
    default_message = "Správa je príliš dlhá na nastavenú dĺžku kontextu."
    default_hint = "Skrať správu, odober prílohu, alebo zväčši dĺžku kontextu."


# --- Úložisko --------------------------------------------------------------


class StorageError(FukaiError):
    default_message = "Prístup k uloženým chatom zlyhal."
    default_hint = "Skontroluj, či je priestor na disku a práva k dátovému adresáru."
    

class DatabaseCorruptError(StorageError):
    default_message = "Databáza chatov je poškodená."
    default_hint = "Zatvor FUKAI a súbor fukai.db premenuj alebo presuň inam. Pri ďalšom štarte vznikne nová, prázdna databáza - chaty z poškodenej DB v nej nebudú, modely áno."


# --- Prílohy ---------------------------------------------------------------


class AttachmentError(FukaiError):
    default_message = "Prílohu sa nepodarilo spracovať."


class UnsupportedAttachmentError(AttachmentError):
    default_message = "Tento typ súboru nie je podporovaný."
    default_hint = "Podporované sú txt, md, csv, json, kód, PDF, xlsx a docx."


class AttachmentTooLargeError(AttachmentError):
    default_message = "Príloha je príliš veľká."
    default_hint = "Rozdeľ súbor na menšie časti."


class AttachmentParseError(AttachmentError):
    default_message = "Zo súboru sa nepodarilo prečítať text."
    default_hint = "Súbor môže byť poškodený, zašifrovaný, alebo obsahovať iba obrázky (OCR nie je podporované)."


# --- Web -------------------------------------------------------------------


class WebSearchError(FukaiError):
    severity = Severity.INFO
    default_message = "Odpoveď je bez informácií z internetu, vyhľadávanie nefungovalo."
    default_hint = "Model odpovedal iba z vlastných znalostí."