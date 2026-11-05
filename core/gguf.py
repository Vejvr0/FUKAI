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


if __name__ == "__main__":
    import sys
    import tempfile
    import time

    def build(kv: list[tuple[str, int, object]], *, version: int = 3, magic: bytes = _MAGIC) -> bytes:
        """Malý GGUF súbor len s hlavičkou. Pole = (typ prvku, zoznam)."""
        def enc_str(s: str) -> bytes:
            raw = s.encode("utf-8")
            return _U64.pack(len(raw)) + raw

        def enc(kind: int, value) -> bytes:
            if kind == _STRING:
                return enc_str(value)
            if kind == _ARRAY:
                item_kind, items = value
                return _U32.pack(item_kind) + _U64.pack(len(items)) + b"".join(enc(item_kind, i) for i in items)
            return struct.pack(_SCALARS[kind], value)

        body = b"".join(enc_str(k) + _U32.pack(t) + enc(t, v) for k, t, v in kv)
        return magic + _U32.pack(version) + _U64.pack(0) + _U64.pack(len(kv)) + body

    llama = [
        ("general.architecture", _STRING, "llama"),
        ("general.name", _STRING, "Test Llama"),
        ("general.size_label", _STRING, "7B"),
        ("general.file_type", 4, 15),
        ("tokenizer.ggml.tokens", _ARRAY, (_STRING, ["<s>", "</s>", "ahoj"])),
        ("tokenizer.ggml.scores", _ARRAY, (6, [0.0, 0.5, 1.0])),
        ("llama.context_length", 4, 4096),
        ("llama.block_count", 4, 32),
        ("llama.embedding_length", 4, 4096),
        ("llama.attention.head_count", 4, 32),
        ("llama.attention.head_count_kv", 4, 8),
        ("tokenizer.chat_template", _STRING, "{{ messages }}"),
    ]
    failed = 0

    def check(label: str, ok: bool) -> None:
        global failed
        failed += not ok
        print(f"  {'OK ' if ok else 'ZLE'} {label}")

    def expect(label: str, data: bytes, error: type[Exception]) -> None:
        path = tmp / "case.gguf"
        path.write_bytes(data)
        started = time.perf_counter()
        try:
            read_header(path)
        except error as exc:
            check(f"{label} → {type(exc).__name__} ({(time.perf_counter() - started) * 1000:.1f} ms): {exc}", True)
        except Exception as exc:
            check(f"{label} → nečakaná {type(exc).__name__}: {exc}", False)
        else:
            check(f"{label} → prešlo, malo spadnúť", False)

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        print("--- syntetický GGUF")
        good = tmp / "good.gguf"
        good.write_bytes(build(llama))
        header = read_header(good)
        check("polia sa preskočia, kľúče za nimi sa prečítajú", "tokenizer.ggml.tokens" not in header
              and header.get("llama.context_length") == 4096)
        meta = read_meta(good)
        print(f"  {meta}")
        check("arch / n_ctx_train / n_layers", (meta.arch, meta.n_ctx_train, meta.n_layers) == ("llama", 4096, 32))
        check("name / quant / size_label", (meta.name, meta.quant, meta.size_label) == ("Test Llama", "Q4_K_M", "7B"))
        check("chat template", meta.has_chat_template is True)
        check("head_dim bez key_length = n_embd / n_head (128)", (meta.head_dim_k, meta.head_dim_v) == (128, 128))
        check("n_head_kv z hlavičky (8)", meta.n_head_kv == 8)

        bare = tmp / "bare.gguf"
        bare.write_bytes(build([kv for kv in llama if kv[0] not in
                                ("llama.attention.head_count_kv", "tokenizer.chat_template", "general.file_type")]))
        meta = read_meta(bare)
        check("bez head_count_kv = head_count (32), bez template, bez file_type",
              (meta.n_head_kv, meta.has_chat_template, meta.quant) == (32, False, None))
        v2 = tmp / "v2.gguf"
        v2.write_bytes(build(llama, version=2))
        check("verzia 2 sa prečíta", read_meta(v2).arch == "llama")
        empty = tmp / "empty.gguf"
        empty.write_bytes(build([]))
        check("hlavička bez kľúčov → samé None", read_meta(empty) == ModelMeta(has_chat_template=False))
        check("round-trip cez to_dict / from_dict", ModelMeta.from_dict(read_meta(good).to_dict()) == read_meta(good))

        print("--- poškodené súbory")
        data = build(llama)
        expect("zlý magic", build(llama, magic=b"GGML"), ModelFormatError)
        expect("verzia 1", build(llama, version=1), ModelFormatError)
        expect("big-endian (verzia 0x03000000)", build(llama, version=3 << 24), ModelFormatError)
        expect("odseknutý v strede", data[: len(data) // 2], ModelFormatError)
        expect("odseknutý v poli reťazcov", data[: data.index(b"ahoj")], ModelFormatError)
        expect("počet kľúčov 2^63", _MAGIC + _U32.pack(3) + _U64.pack(0) + _U64.pack(1 << 63), ModelFormatError)
        expect("dĺžka kľúča 2^60", _MAGIC + _U32.pack(3) + _U64.pack(0) + _U64.pack(1) + _U64.pack(1 << 60), ModelFormatError)
        expect("pole reťazcov s 2^40 prvkami", build([("x", _ARRAY, (_STRING, []))])[:-8] + _U64.pack(1 << 40), ModelFormatError)
        expect("pole polí", build([("x", _ARRAY, (_ARRAY, []))]), ModelFormatError)
        expect("neznámy typ 13", build([("x", 4, 1)]).replace(_U32.pack(4), _U32.pack(13)), ModelFormatError)
        expect("prázdny súbor", b"", ModelFormatError)
        try:
            read_header(tmp / "nie_je.gguf")
            check("neexistujúci súbor", False)
        except ModelNotFoundError:
            check("neexistujúci súbor → ModelNotFoundError", True)
        try:
            read_header(tmp)
            check("adresár", False)
        except ModelNotFoundError:
            check("adresár → ModelNotFoundError", True)

    for arg in sys.argv[1:]:
        started = time.perf_counter()
        meta = read_meta(arg)
        print(f"\n{Path(arg).name}  ({(time.perf_counter() - started) * 1000:.0f} ms)")
        for key, value in meta.to_dict().items():
            print(f"  {key:18} {value}")

    print("\nVŠETKO OK" if not failed else f"\nZLYHALO: {failed}")
    sys.exit(1 if failed else 0)
