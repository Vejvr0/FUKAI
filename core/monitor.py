"""Vyťaženie CPU, GPU a pamäte pre monitor v hlavičke chatu.

Zásada je tá istá ako v `core/hardware.py`: **sonda nikdy nevyhodí výnimku von.** Keď sa
hodnota nedá zistiť, je `None` a UI ukáže pomlčku – monitor je informácia, nie funkcia,
bez ktorej by appka nemohla bežať.

Vzorkuje sa raz za sekundu z UI vlákna, takže nič tu nesmie blokovať:
- `psutil.cpu_percent(interval=None)` je priemer od posledného volania, teda bez čakania;
- NVML je volanie do ovládača, namerané 0,25 ms na vzorku (PC 1, RTX 5060 Ti);
- macOS nemá na vyťaženie GPU verejné API (`powermetrics` chce root), zostáva `ioreg`,
  ktorý je subprocess za desiatky ms. Preto sa **nečaká naň**: `sample()` proces spustí
  a jeho výsledok vyzdvihne až nasledujúce volanie. Číslo je tak o jeden tik staršie,
  čo pri sekundovom monitore nevadí, a UI nezamrzne ani raz.
"""
from __future__ import annotations
import platform
import re
import subprocess
from dataclasses import dataclass

import psutil

from core.hardware import HardwareProfile, free_ram_mb

__all__ = ["Usage", "UsageMonitor"]

_IOREG = ("ioreg", "-r", "-d", "1", "-c", "IOAccelerator", "-w", "0")
_IOREG_KEYS = (re.compile(r'"Device Utilization %"\s*=\s*(\d+)'),
               re.compile(r'"GPU Activity\(%\)"\s*=\s*(\d+)'))
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass(frozen=True)
class Usage:
    """Percentá pre tri riadky monitora. `None` = nedá sa zistiť."""
    cpu: float | None = None
    gpu: float | None = None
    memory: float | None = None
    memory_label: str = "RAM"


class UsageMonitor:
    """Vlastní NVML spojenie a rozbehnutú `ioreg` sondu, preto ho treba `close()`-núť.
    Vytvára ho `Application` a podáva oknu, ako ostatné služby."""

    def __init__(self, hardware: HardwareProfile) -> None:
        self._hardware = hardware
        self._nvml = None               # modul pynvml, kým sa darí
        self._handle = None
        self._nvml_dead = False
        self._ioreg: subprocess.Popen | None = None
        self._gpu_macos: float | None = None
        # prvé volanie `cpu_percent` vracia 0.0 – meria sa od štartu procesu
        psutil.cpu_percent(interval=None)

    @property
    def memory_label(self) -> str:
        """VRAM len pri backende, ktorý má vlastnú pamäť. Na Metale je GPU pamäť tá istá
        RAM (§4), a pri CPU builde na stroji s NVIDIA kartou beží model tiež v RAM."""
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

    # --- CPU a pamäť ---------------------------------------------------------------

    @staticmethod
    def _cpu_percent() -> float | None:
        try:
            return psutil.cpu_percent(interval=None)
        except Exception:
            return None

    def _ram_percent(self) -> float | None:
        """Cez `free_ram_mb()`, nie `virtual_memory().percent` – appka na tom istom čísle
        stavia varovania pred načítaním modelu a na macOS je psutil mimo (§4)."""
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

    # --- GPU -----------------------------------------------------------------------

    def _gpu_percent(self) -> float | None:
        gpu = self._hardware.gpu
        if gpu is None:
            return 0.0                  # bez karty je riadok nula, nie pomlčka
        if gpu.backend == "metal":
            return self._gpu_percent_macos()
        rates = self._nvml_call(lambda nvml, handle: nvml.nvmlDeviceGetUtilizationRates(handle))
        return None if rates is None else float(rates.gpu)

    def _nvml_call(self, call):
        if self._nvml_dead:
            return None
        try:
            if self._nvml is None:
                import pynvml                      # lenivo: na Macu balík nie je (§3)
                pynvml.nvmlInit()                  # jednorazovo ~17 ms
                self._nvml = pynvml
                self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            return call(self._nvml, self._handle)
        except Exception:
            self._nvml_dead = True                 # neskúšať pri každom tiku znova
            self._nvml, self._handle = None, None
            return None

    def _gpu_percent_macos(self) -> float | None:
        """Vyzdvihne výsledok predchádzajúceho behu a hneď spustí ďalší – pozri docstring
        modulu. Kým prvý nedobehne, je hodnota `None`."""
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
    """Prvý akcelerátor, ktorý hlási vyťaženie. Na Macoch s dvoma GPU je prvý ten
    integrovaný; FUKAI na Apple Silicon iný nemá."""
    for pattern in _IOREG_KEYS:
        match = pattern.search(output)
        if match is not None:
            try:
                return max(0.0, min(100.0, float(match.group(1))))
            except ValueError:
                return None
    return None


if __name__ == "__main__":
    import sys
    import time
    from core.hardware import detect

    hardware = detect()
    monitor = UsageMonitor(hardware)
    print(f"backend={hardware.backend}  gpu={hardware.gpu.name if hardware.gpu else None}  "
          f"tretí riadok={monitor.memory_label}")
    try:
        for _ in range(int(sys.argv[1]) if len(sys.argv) > 1 else 5):
            time.sleep(1.0)
            start = time.perf_counter()
            usage = monitor.sample()
            took = 1000 * (time.perf_counter() - start)
            text = "  ".join(f"{name}: {'–' if value is None else f'{value:.0f} %'}"
                             for name, value in (("CPU", usage.cpu), ("GPU", usage.gpu),
                                                 (usage.memory_label, usage.memory)))
            print(f"{text}   (vzorka {took:.2f} ms)")
    finally:
        monitor.close()
