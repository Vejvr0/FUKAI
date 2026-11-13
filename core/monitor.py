# --- ./core/monitor.py ---


from __future__ import annotations
import platform
import re
import subprocess
from dataclasses import dataclass
import psutil
from core.hardware import HardwareProfile, free_ram_mb

__all__ = [
    "Usage",
    "UsageMonitor"
]

_IOREG = ("ioreg", "-r", "-d", "1", "-c", "IOAccelerator", "-w", "0")
_IOREG_KEYS = (
    re.compile(r'"Device Utilization %"\s*=\s*(\d+)'),
    re.compile(r'"GPU Activity\(%\)"\s*=\s*(\d+)')
)
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass(frozen=True)
class Usage:
    cpu: float | None = None
    gpu: float | None = None
    memory: float | None = None
    memory_label: str = "RAM"


class UsageMonitor:
    def __init__(self, hardware: HardwareProfile) -> None:
        self._hardware = hardware
        self._nvml = None
        self._handle = None
        self._nvml_dead = False
        self._ioreg: subprocess.Popen | None = None
        self._gpu_macos: float | None = None
        psutil.cpu_percent(interval=None)


    @property
    def memory_label(self) -> str:
        gpu = self._hardware.gpu
        if self._hardware.backend == "cuda" and gpu is not None and gpu.vram_total_mb:
            return "VRAM"
        return "RAM"


    def sample(self) -> Usage:
        label = self.memory_label
        memory = self._vram_percent() if label == "VRAM" else self._ram_percent()
        return Usage(cpu=self._cpu_percent(), gpu=self._gpu_percent(),
                     memory=memory, memory_label=label)


    def close(self) -> None:
        if self._nvml is not None:
            try:
                self._nvml.nvmlShutdown()
            except Exception:
                pass
            self._nvml, self._handle = None, None
        self._kill_ioreg()
        

    @staticmethod
    def _cpu_percent() -> float | None:
        try:
            return psutil.cpu_percent(interval=None)
        except Exception:
            return None
        

    def _ram_percent(self) -> float | None:
        total = self._hardware.ram_total_mb
        if not total:
            return None
        try:
            return max(0.0, min(100.0, 100.0 * (total - free_ram_mb()) / total))
        except Exception:
            return None


    def _vram_percent(self) -> float | None:
        info = self._nvml_call(lambda nvml, handle: nvml.nvmlDeviceGetMemoryInfo(handle))
        if info is None or not info.total:
            return None
        return 100.0 * info.used / info.total


    def _gpu_percent(self) -> float | None:
        gpu = self._hardware.gpu
        if gpu is None:
            return 0.0
        if gpu.backend == "metal":
            return self._gpu_percent_macos()
        rates = self._nvml_call(lambda nvml, handle: nvml.nvmlDeviceGetUtilizationRates(handle))
        return None if rates is None else float(rates.gpu)
    

    def _nvml_call(self, call):
        if self._nvml_dead:
            return None
        try:
            if self._nvml is None:
                import pynvml # pyright: ignore[reportMissingImports]
                pynvml.nvmlInit()
                self._nvml = pynvml
                self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            return call(self._nvml, self._handle)
        except Exception:
            self._nvml_dead = True
            self._nvml, self._handle = None, None
            return None
        

    def _gpu_percent_macos(self) -> float | None:
        process = self._ioreg
        if process is not None and process.poll() is not None:
            self._ioreg = None
            try:
                output = process.stdout.read() if process.stdout is not None else ""
            except Exception:
                output = ""
            self._gpu_macos = _parse_ioreg(output)
        if self._ioreg is None:
            self._ioreg = _start_ioreg()
        return self._gpu_macos


    def _kill_ioreg(self) -> None:
        process, self._ioreg = self._ioreg, None
        if process is None:
            return
        try:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=1)
        except Exception:
            pass


def _start_ioreg() -> subprocess.Popen | None:
    if platform.system() != "Darwin":
        return None
    try:
        return subprocess.Popen(_IOREG, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, errors="replace", creationflags=_NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return None


def _parse_ioreg(output: str) -> float | None:
    for pattern in _IOREG_KEYS:
        match = pattern.search(output)
        if match is not None:
            try:
                return max(0.0, min(100.0, float(match.group(1))))
            except ValueError:
                return None
    return None
