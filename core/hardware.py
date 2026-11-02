import json
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
import platform
import psutil
from core.constants import HW_CONF, RELATION_PROCESSOR_CORE, ERROR_INSUFFICIENT_BUFFER
from core.errors import ConfigError, Notice


@dataclass
class GpuInfo:
    name: str
    backend: str                # 'cuda' alebo 'metal'
    vram_total_mb: int | None   # pri Metal None – pamäť je zdieľaná s RAM
    vram_free_mb: int | None
    compute: str | None         # compute capability, napr. '12.0'; iba pri CUDA


@dataclass
class HardwareProfile:
    system: str             # 'Windows' alebo 'Darwin'
    release: str            # verzia OS na zobrazenie, napr. '11' alebo '15.6.1'
    os_version: int         # to iste ako cislo na porovnavanie, pozri _os_version()
    cores_physical: int     # skutočné jadrá
    cores_logical: int      # jadrá vrátane HyperThreadingu
    cores_performance: int  # výkonné (P) jadrá; na nehybridnom CPU = cores_physical
    ram_total_mb: int       # celková RAM
    ram_available_mb: int   # koľko je jej práve voľnej
    gpu: GpuInfo | None     # None = nenašla sa použiteľná grafika

    @property
    def hybrid(self) -> bool:
        return self.cores_performance < self.cores_physical

    @property
    def n_threads(self) -> int:
        return max(1, self.cores_performance)

    @property
    def backend(self) -> str:
        return self.gpu.backend if self.gpu else "cpu"

    @property
    def n_gpu_layers(self) -> int:
        return -1 if self.gpu else 0


def _os_version() -> tuple[str, int]:
    system = platform.system()
    if system == "Windows":
        parts = platform.version().split(".")
        build = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 0
        return platform.release(), build

    if system == "Darwin":
        version = platform.mac_ver()[0]
        major = int(version.split(".")[0]) if version else 0
        return version, major

    return platform.release(), 0


def _performance_cores_windows() -> int | None:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    probe = kernel32.GetLogicalProcessorInformationEx
    probe.argtypes = [ctypes.c_ulong, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)]
    probe.restype = wintypes.BOOL

    size = wintypes.DWORD(0)
    if not probe(RELATION_PROCESSOR_CORE, None, ctypes.byref(size)):
        if ctypes.get_last_error() != ERROR_INSUFFICIENT_BUFFER:
            return None
    if size.value == 0:
        return None

    buffer = (ctypes.c_byte * size.value)()
    if not probe(RELATION_PROCESSOR_CORE, ctypes.byref(buffer), ctypes.byref(size)):
        return None

    raw = bytes(buffer)
    counts: dict[int, int] = {}
    offset = 0
    while offset + 10 <= len(raw):
        record_size = int.from_bytes(raw[offset + 4:offset + 8], "little")
        if record_size == 0:
            break
        trieda = raw[offset + 9]
        counts[trieda] = counts.get(trieda, 0) + 1
        offset += record_size

    if len(counts) < 2:
        return None
    return counts[max(counts)]


def _performance_cores_macos() -> int | None:
    if platform.machine() != "arm64":
        return None
    try:
        done = subprocess.run(
            ["sysctl", "-n", "hw.perflevel0.physicalcpu"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = done.stdout.strip()
    return int(value) if value.isdigit() else None


def _performance_cores(cores_physical: int) -> int:
    system = platform.system()
    try:
        if system == "Windows":
            found = _performance_cores_windows()
        elif system == "Darwin":
            found = _performance_cores_macos()
        else:
            found = None
    except Exception:
        found = None

    if found and 0 < found <= cores_physical:
        return found
    return cores_physical


def _free_ram_mb_macos() -> int | None:
    try:
        done = subprocess.run(
            ["vm_stat"], capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    page_size = 16384
    pages: dict[str, int] = {}
    for line in done.stdout.splitlines():
        if "page size of" in line:
            page_size = int(line.split("page size of")[1].split()[0])
            continue
        key, sep, value = line.partition(":")
        value = value.strip().rstrip(".")
        if sep and value.isdigit():
            pages[key.strip()] = int(value)

    try:
        held = (pages["Anonymous pages"] - pages["Pages purgeable"]
                + pages["Pages wired down"] + pages["Pages occupied by compressor"])
    except KeyError:
        return None
    return max(0, psutil.virtual_memory().total - held * page_size) // 1024 // 1024


def free_ram_mb() -> int:
    if platform.system() == "Darwin":
        try:
            found = _free_ram_mb_macos()
        except Exception:
            found = None
        if found is not None:
            return found
    return psutil.virtual_memory().available // 1024 // 1024


def _probe_nvidia() -> GpuInfo | None:
    if shutil.which("nvidia-smi") is None:
        return None

    try:
        done = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=name,memory.total,memory.free,compute_cap",
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if done.returncode != 0 or not done.stdout.strip():
        return None
    
    arr = [p.strip() for p in done.stdout.strip().splitlines()[0].split(",")]
    if len(arr) < 4:
        return None

    try:
        return GpuInfo(
            name=arr[0],
            backend="cuda",
            vram_total_mb=int(arr[1]),
            vram_free_mb=int(arr[2]),
            compute=arr[3],
        )
    except ValueError:
        return None


def _probe_metal() -> GpuInfo | None:
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return None

    return GpuInfo(
        name="Apple Silicon (integrovaná grafika)",
        backend="metal",
        vram_total_mb=None,
        vram_free_mb=None,
        compute=None,
    )


def detect_gpu() -> GpuInfo | None:
    return _probe_nvidia() or _probe_metal()


def required_wheel(profil: HardwareProfile) -> str | None:
    if profil.gpu is None or profil.gpu.backend != "cuda":
        return None
    return gpu_arch(profil.gpu.compute)[1]


def gpu_arch(compute: str | None) -> tuple[str | None, str | None]:
    if compute is None:
        return None, None
    try:
        write = get_allowed_hw()["cuda_arch"].get(compute)
    except (ConfigError, KeyError, json.JSONDecodeError):
        return None, None
    if not isinstance(write, dict):
        return None, None
    return write.get("name"), write.get("wheel")


def detect() -> HardwareProfile:
    ram = psutil.virtual_memory()
    release, os_version = _os_version()
    cores_physical = psutil.cpu_count(logical=False)
    return HardwareProfile(
        gpu=detect_gpu(),
        system=platform.system(),
        release=release,
        os_version=os_version,
        cores_physical=cores_physical,
        cores_logical=psutil.cpu_count(logical=True),
        cores_performance=_performance_cores(cores_physical),
        ram_total_mb=ram.total // 1024 // 1024,
        ram_available_mb=free_ram_mb(),
    )


@lru_cache(maxsize=1)
def get_allowed_hw():
    if not HW_CONF.exists():
        raise ConfigError(f"Chýba súbor {HW_CONF}")
    with open(HW_CONF, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {
        "platforms": data['minimum_os'],
        "cores": data['minimum_cores'],
        "ram_mb": data['minimum_ram_gb'] * 1024,
        "cuda_arch": data['cuda_arch'],
    }


def check_os(profil: HardwareProfile) -> Notice | None:
    try:
        data = get_allowed_hw()
    except (ConfigError, KeyError, json.JSONDecodeError) as exc:
        return Notice.warning(
            "Podporované verzie systému sa nepodarilo načítať, kontrola bola preskočená.",
            detail=f"{type(exc).__name__}: {exc}",
        )

    allowed = data["platforms"].get(profil.system)
    if allowed is None:
        return Notice.warning(
            f"FUKAI nie je testovaný na systéme {profil.system}.",
            hint="Aplikácia pobeží, ale môžu sa vyskytnúť neočakávané problémy.",
        )

    if profil.os_version < allowed["minimum"]:
        return Notice.error(
            f"Tvoj systém je starší, než FUKAI podporuje. "
            f"Potrebný je aspoň {allowed['label']}.",
            detail=f"zistene: {allowed['compare']}={profil.os_version}, minimum: {allowed['minimum']}",
        )

    return None


def check_cores(profil: HardwareProfile) -> Notice | None:
    try:
        data = get_allowed_hw()
    except (ConfigError, KeyError, json.JSONDecodeError) as exc:
        return Notice.warning(
            "Požiadavky aplikácie neboli zistené, kontrola bola preskočená.",
            detail=f"{type(exc).__name__}: {exc}",
        )
    
    allowed = data["cores"]
    if profil.cores_logical < allowed:
        return Notice.warning(
            "Tvoje zariadenie má málo CPU jadier, odpovede budú pomalé.",
            hint=f"Odporúčaný počet logických jadier je {allowed}.",
            detail=f"zistené: {profil.cores_logical}, minimum: {allowed}",
        )

    return None

def check_ram(profil: HardwareProfile) -> Notice | None:
    try:
        data = get_allowed_hw()
    except (ConfigError, KeyError, json.JSONDecodeError) as exc:
        return Notice.warning(
            "Požiadavky aplikácie neboli zistené, kontrola bola preskočená.",
            detail=f"{type(exc).__name__}: {exc}",
        )

    allowed = data["ram_mb"]
    if profil.ram_available_mb < allowed:
        free_gb = f"{profil.ram_available_mb / 1024:.1f}".replace(".", ",")
        return Notice.warning(
            "Voľná pamäť RAM nemusí na model stačiť.",
            hint=f"Voľných je {free_gb} GB, odporúča sa aspoň {allowed / 1024:.0f} GB pre najmenšie modely. Skús zatvoriť iné aplikácie.",
            detail=f"zistené: {profil.ram_available_mb} MB, minimum: {allowed} MB",
        )

    return None


def check_gpu(profil: HardwareProfile) -> Notice | None:
    if profil.gpu is None:
        return Notice.warning(
            "Nenašla sa podporovaná GPU, model pobeží na CPU.",
            hint="Odpovede budú výrazne pomalšie. FUKAI akceleruje na NVIDIA (CUDA) a Apple Silicon (Metal).",
        )

    if profil.gpu.backend != "cuda":
        return None

    if gpu_arch(profil.gpu.compute)[1] is None:
        return Notice.warning(
            f"Pre tvoju grafickú kartu nie je známy predkompilovaný wheel (compute capability {profil.gpu.compute}).",
            hint="Pozri requirements-llama-win-cuda.txt.",
        )

    return None


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    profil = detect()
    print(f"Systém:     {profil.system} {profil.release}  (porovnáva sa {profil.os_version})")
    print(f"Jadrá:      {profil.cores_physical} fyzických / {profil.cores_logical} logických"
          + (f" / {profil.cores_performance} výkonných" if profil.hybrid else " (nehybridné)"))
    print(f"RAM:        {profil.ram_total_mb / 1024:.1f} GB celkom")
    print(f"RAM voľná:  {profil.ram_available_mb / 1024:.1f} GB")

    if profil.gpu:
        arch, wheel = gpu_arch(profil.gpu.compute)
        print(f"Grafika:    {profil.gpu.name}")
        if profil.gpu.vram_total_mb:
            print(f"VRAM:       {profil.gpu.vram_total_mb / 1024:.1f} GB celkom, "
                  f"{profil.gpu.vram_free_mb / 1024:.1f} GB voľnej")
        print(f"Architekt.: {arch or 'neznáma'}  (compute {profil.gpu.compute}, wheel {wheel or '?'})")
    else:
        print("Grafika:    nenašla sa")

    print(f"\nBackend:      {profil.backend}")
    print(f"n_threads:    {profil.n_threads}")
    print(f"n_gpu_layers: {profil.n_gpu_layers}")

    print("\nKontroly:")
    for nazov, fn in (("OS", check_os), ("CPU", check_cores),
                      ("RAM", check_ram), ("GPU", check_gpu)):
        vysledok = fn(profil)
        print(f"  {nazov:4} {vysledok.log_line() if vysledok else 'prešla'}")
