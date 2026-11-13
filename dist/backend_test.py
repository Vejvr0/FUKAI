# --- ./dist/backend_test.py ---


import json
import sys
from pathlib import Path


def run(app_dir: Path) -> dict:
    result = {
        "ok": False,
        "backend": None,
        "llama_cpp": None,
        "gpu_offload": None,
        "gpu": None,
        "vram_mb": None,
        "error": None
    }
    sys.path.insert(0, str(app_dir))
    try:
        from core.hardware import detect
        from core.llm_engine import probe_engine
        engine = probe_engine()
        hw = detect(gpu_offload=engine.gpu_offload)
    except Exception as exc:
        message = getattr(exc, "message", None) or type(exc).__name__
        detail = getattr(exc, "detail", None) or str(exc)
        result["error"] = f"{message} | {detail}"
        return result
    result.update(
        ok=True,
        backend=hw.backend,
        llama_cpp=engine.version,
        gpu_offload=engine.gpu_offload,
        gpu=hw.gpu.name if hw.gpu else None,
        vram_mb=hw.gpu.vram_total_mb if hw.gpu else None
    )
    return result


def main() -> int:
    if len(sys.argv) != 2:
        print("použitie: backend_test.py <priečinok appky>", file=sys.stderr)
        return 2
    result = run(Path(sys.argv[1]).resolve())
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
