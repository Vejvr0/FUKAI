import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

DIST = Path(__file__).resolve().parent
REPO = DIST.parent
UV = DIST / "tools" / "uv"
PLATFORMS = {"macos": "aarch64-apple-darwin", "windows": "x86_64-pc-windows-msvc"}
EXTRA = {"cuda": [DIST / "requirements-nvidia.txt"]}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def wheel_path(name: str, backend: dict) -> Path:
    return DIST / "backend_whls" / backend["wheel"]["release"] / backend["wheel"]["file"]


def check_wheels(backends: dict) -> None:
    for name, backend in backends.items():
        wheel = wheel_path(name, backend)
        if not wheel.is_file():
            sys.exit(f"{name}: chýba {wheel.relative_to(REPO)}")
        if sha256(wheel) != backend["wheel"]["sha256"]:
            sys.exit(f"{name}: {wheel.relative_to(REPO)} má iný hash než manifest")


def lock(name: str, backend: dict, python: str, tmp: Path) -> None:
    source = tmp / f"{name}.in"
    source.write_text(f"llama_cpp_python @ {wheel_path(name, backend).as_uri()}\n", encoding="utf-8")
    out = DIST / backend["lock"]
    out.parent.mkdir(exist_ok=True)
    result = subprocess.run([
        str(UV), "pip", "compile",
        str(REPO / "requirements.txt"), *map(str, EXTRA.get(name, [])), str(source),
        "--python-version", python,
        "--python-platform", PLATFORMS[backend["os"]],
        "--generate-hashes",
        "--no-emit-package", "llama-cpp-python",
        "--no-annotate", "--no-header", "--quiet",
        "-o", str(out),
    ])
    if result.returncode != 0:
        sys.exit(f"{name}: uv pip compile zlyhal (kód {result.returncode}), príčina je vypísaná vyššie")
    packages = sum(1 for line in out.read_text(encoding="utf-8").splitlines() if line[:1].isalnum())
    print(f"{out.relative_to(REPO)}: {packages} balíkov", flush=True)


def main() -> None:
    if not UV.is_file():
        sys.exit(f"Chýba {UV.relative_to(REPO)} – stiahni uv podľa manifest.json (uv.macos).")
    manifest = json.loads((DIST / "manifest.json").read_text(encoding="utf-8"))
    check_wheels(manifest["backends"])
    with tempfile.TemporaryDirectory() as tmp:
        for name, backend in manifest["backends"].items():
            lock(name, backend, manifest["python"], Path(tmp))


if __name__ == "__main__":
    main()
