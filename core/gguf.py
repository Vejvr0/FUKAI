# --- ./core/gguf.py ---


from __future__ import annotations
import struct
from pathlib import Path
from typing import BinaryIO
from core.constants import (
    META_ARCH, META_BLOCK_COUNT, META_CHAT_TEMPLATE, META_CONTEXT_LENGTH,
    META_FILE_TYPE, META_EMBEDDING_LENGTH, META_HEAD_COUNT, META_HEAD_COUNT_KV,
    META_KEY_LENGTH, META_NAME, META_SIZE_LABEL, META_VALUE_LENGTH, ARCH_PROJECTOR
)
from core.settings import ModelMeta
from core.errors import ModelError, ModelFormatError, ModelNotFoundError

__all__ = [
    "check_usable",
    "read_header",
    "read_meta"
]


_MAGIC = b"GGUF"
_VERSIONS = (2, 3)
_STRING = 8
_ARRAY = 9
_SCALARS = {
    0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i",
    6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d",
}
_U32 = struct.Struct("<I")
_U64 = struct.Struct("<Q")
_MIN_KV_SIZE = 8 + 4 + 1
_FILE_TYPES = {
    0: "F32", 1: "F16", 2: "Q4_0", 3: "Q4_1", 7: "Q8_0", 8: "Q5_0", 9: "Q5_1",
    10: "Q2_K", 11: "Q3_K_S", 12: "Q3_K_M", 13: "Q3_K_L", 14: "Q4_K_S", 15: "Q4_K_M",
    16: "Q5_K_S", 17: "Q5_K_M", 18: "Q6_K", 19: "IQ2_XXS", 20: "IQ2_XS", 21: "Q2_K_S",
    22: "IQ3_XS", 23: "IQ3_XXS", 24: "IQ1_S", 25: "IQ4_NL", 26: "IQ3_S", 27: "IQ3_M",
    28: "IQ2_S", 29: "IQ2_M", 30: "IQ4_XS", 31: "IQ1_M", 32: "BF16", 36: "TQ1_0",
    37: "TQ2_0", 38: "MXFP4_MOE", 39: "NVFP4", 40: "Q1_0", 41: "Q2_0",
}


class _Reader:
    def __init__(self, f: BinaryIO, size: int) -> None:
        self._f = f
        self._size = size
    
    
    def remaining(self) -> int:
        return self._size - self._f.tell()
    
    
    def take(self, n: int) -> bytes:
        data = self._f.read(n)
        if len(data) != n:
            raise ModelFormatError("hlavička GGUF je odseknutá")
        return data

    
    def u32(self) -> int:
        return _U32.unpack(self.take(4))[0]
    
    
    def u64(self) -> int:
        return _U64.unpack(self.take(8))[0]
    
    
    def count(self, unit: int) -> int:
        n = self.u64()
        if n * unit > self.remaining():
            raise ModelFormatError(f"nezmyselná dĺžka v hlavičke GGUF: {n}")
        return n
    
    
    def string(self) -> str:
        return self.take(self.count(1)).decode("utf-8", errors="replace")
    
    
    def value(self, kind: int):
        if kind == _STRING:
            return self.string()
        if kind == _ARRAY:
            self._skip_array()
            return None
        fmt = _SCALARS.get(kind)
        if fmt is None:
            raise ModelFormatError(f"neznámy typ hodnoty v hlavičke GGUF: {kind}")
        return struct.unpack(fmt, self.take(struct.calcsize(fmt)))[0]
    
    
    def _skip_array(self) -> None:
        kind = self.u32()
        if kind == _STRING:
            n = self.count(8)
            f, unpack, read = self._f, _U64.unpack, self._f.read
            for _ in range(n):
                raw = read(8)
                if len(raw) != 8:
                    raise ModelFormatError("hlavička GGUF je odseknutá")
                f.seek(unpack(raw)[0], 1)
            if self.remaining() < 0:
                raise ModelFormatError("hlavička GGUF je odseknutá")
            return
        fmt = _SCALARS.get(kind)
        if fmt is None:
            raise ModelFormatError(f"nepodporovaný typ poľa v hlavičke GGUF: {kind}")
        self._f.seek(self.count(struct.calcsize(fmt)) * struct.calcsize(fmt), 1)
    
    
def read_header(path: str | Path) -> dict[str, object]:
    path = Path(path)
    try:
        with path.open("rb") as f:
            reader = _Reader(f, path.stat().st_size)
            if reader.take(4) != _MAGIC:
                raise ModelFormatError(f"chýba GGUF hlavička: {path}")
            version = reader.u32()
            if version not in _VERSIONS:
                raise ModelFormatError(f"nepodporovaná verzia GGUF {version}: {path}")
            reader.u64()
            n_kv = reader.count(_MIN_KV_SIZE)
            header: dict[str, object] = {}
            for _ in range(n_kv):
                key = reader.string()
                value = reader.value(reader.u32())
                if value is not None:
                    header[key] = value
            return header
    except (FileNotFoundError, IsADirectoryError) as exc:
        raise ModelNotFoundError(f"súbor neexistuje: {path}") from exc
    except OSError as exc:
        raise ModelError(f"{type(exc).__name__}: {exc}") from exc


def read_meta(path: str | Path) -> ModelMeta:
    header = read_header(path)
    arch = _text(header.get(META_ARCH))
    
    
    def arch_int(suffix: str) -> int | None:
        return _int(header.get(f"{arch}.{suffix}")) if arch else None
    
    
    n_head = arch_int(META_HEAD_COUNT)
    n_embd = arch_int(META_EMBEDDING_LENGTH)
    head_dim = n_embd // n_head if n_embd and n_head else None
    head_dim_k = arch_int(META_KEY_LENGTH) or head_dim
    template = header.get(META_CHAT_TEMPLATE)
    
    return ModelMeta(
        arch=arch,
        n_ctx_train=arch_int(META_CONTEXT_LENGTH),
        n_layers=arch_int(META_BLOCK_COUNT),
        name=_text(header.get(META_NAME)),
        quant=_FILE_TYPES.get(_int(header.get(META_FILE_TYPE))),
        size_label=_text(header.get(META_SIZE_LABEL)),
        has_chat_template=isinstance(template, str) and bool(template.strip()),
        n_head_kv=arch_int(META_HEAD_COUNT_KV) or n_head,
        head_dim_k=head_dim_k,
        head_dim_v=arch_int(META_VALUE_LENGTH) or head_dim_k 
    )


def check_usable(meta: ModelMeta) -> None:
    if meta.arch == ARCH_PROJECTOR:
        raise ModelFormatError(
            f"general.architecture = {meta.arch}",
            message="Súbor je vizuálny projektor (mmproj), nie jazykový model.",
            hint="Vyber samotný model - súbor bez „mmproj“ v názve."
        )
    if meta.arch is None or meta.n_layers is None:
        raise ModelFormatError(
            f"general.architecture = {meta.arch}, block_count = {meta.n_layers}",
            message="Súbor nie je jazykový model."
        )
    if not meta.has_chat_template:
        raise ModelFormatError(
            "chýba tokenizer.chat_template",
            message="Model nemá v metadátach chat template.",
            hint="FUKAI ho potrebuje na skladanie konverzácie. Stiahni verziu modelu s chat template (zvyčajne s „-it“ alebo „-instruct“ v názve)."
        )


def _int(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _text(value) -> str | None:
    return (value.strip() or None) if isinstance(value, str) else None
