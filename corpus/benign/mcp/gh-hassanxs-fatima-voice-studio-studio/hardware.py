"""What this PC has (GPU, memory, CPU, disk, power) and what to run on it."""
import ctypes
import os
import shutil
import subprocess
import winreg
from pathlib import Path

from . import config

_DISPLAY_CLASS = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
_SKIP = ("microsoft basic", "remote", "virtual", "parsec", "meta virtual", "idd")
_cache: dict | None = None


def _vendor(name: str) -> str:
    n = name.lower()
    return "nvidia" if "nvidia" in n else "amd" if ("amd" in n or "radeon" in n) else "intel" if "intel" in n else "other"


def _nvidia_smi() -> list[dict]:
    exe = shutil.which("nvidia-smi") or r"C:\Windows\System32\nvidia-smi.exe"
    try:
        out = subprocess.run([exe, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    gpus = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 3:
            gpus.append({"name": parts[0], "vendor": "nvidia", "vram_gb": round(float(parts[1]) / 1024, 1),
                         "driver": parts[2], "integrated": False})
    return gpus


def _registry_gpus() -> list[dict]:
    """Display adapters from the registry. Unlike WMI, it reports VRAM above 4 GB."""
    gpus = []
    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _DISPLAY_CLASS)
    except OSError:
        return gpus
    for i in range(64):
        try:
            sub = winreg.EnumKey(root, i)
        except OSError:
            break
        if not sub.isdigit():
            continue
        try:
            with winreg.OpenKey(root, sub) as k:
                name = winreg.QueryValueEx(k, "DriverDesc")[0]
                try:
                    mem = int(winreg.QueryValueEx(k, "HardwareInformation.qwMemorySize")[0])
                except OSError:
                    mem = 0
        except OSError:
            continue
        if any(s in name.lower() for s in _SKIP):
            continue
        vram = round(mem / 1024**3, 1)
        # Integrated graphics share system memory and report little or none of their own.
        gpus.append({"name": name, "vendor": _vendor(name), "vram_gb": vram, "driver": None,
                     "integrated": vram < 2 or (_vendor(name) == "intel" and "arc" not in name.lower())})
    return gpus


def _ram_gb() -> float:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    m = MEMORYSTATUSEX()
    m.dwLength = ctypes.sizeof(m)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return round(m.ullTotalPhys / 1024**3, 1)


def _cpu() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
            return winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
    except OSError:
        return "Unknown CPU"


def on_battery() -> bool | None:
    class SYSTEM_POWER_STATUS(ctypes.Structure):
        _fields_ = [("ACLineStatus", ctypes.c_byte), ("BatteryFlag", ctypes.c_byte),
                    ("BatteryLifePercent", ctypes.c_byte), ("SystemStatusFlag", ctypes.c_byte),
                    ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]
    s = SYSTEM_POWER_STATUS()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)) or s.BatteryFlag & 128:  # 128 = no battery
        return None
    return s.ACLineStatus == 0


def detect(refresh: bool = False) -> dict:
    """GPUs, RAM and CPU. Cached: hardware doesn't change while the app runs."""
    global _cache
    if _cache is None or refresh:
        nv = _nvidia_smi()
        others = [g for g in _registry_gpus() if not (g["vendor"] == "nvidia" and nv)]
        gpus = sorted(nv + others, key=lambda g: (g["integrated"], -g["vram_gb"]))
        _cache = {"gpus": gpus, "ram_gb": _ram_gb(), "cpu": _cpu(), "cores": os.cpu_count() or 0}
    return _cache


def main_gpu(hw: dict) -> dict | None:
    """The card speech will run on: the biggest dedicated one."""
    return next((g for g in hw["gpus"] if not g["integrated"]), None)


def _driver_major(g: dict) -> float | None:
    try:
        return float(str(g.get("driver") or "").split(".")[0])
    except ValueError:
        return None


def recommended_engine(hw: dict) -> str:
    g = main_gpu(hw)
    if g and g["vendor"] == "nvidia":
        major = _driver_major(g)
        old_card = any(k in g["name"].upper() for k in ("GTX 10", "GTX 9", "TITAN X", "QUADRO P"))
        # CUDA 13 builds need a 580+ driver (2025) and a GTX 16 / RTX card or newer.
        return "cuda12" if old_card or (major is not None and major < 580) else "cuda"
    if g:
        return "vulkan"
    return "cpu"


def model_fit(key: str, hw: dict, engine: str) -> str:
    """'fits' (runs fully on the GPU), 'tight' (little room to spare), 'too_big', 'cpu', or 'unsupported' (a model
    whose runtime has no build for this engine, like S2 Pro on the CPU)."""
    m = config.MODELS[key]
    if m.get("engines") and engine not in m["engines"]:
        return "unsupported"
    if m["kind"] != "voice" or not config.ENGINES[engine]["gpu"] or not main_gpu(hw):
        return "cpu"  # Whisper always runs on the CPU
    vram = main_gpu(hw)["vram_gb"]
    if m["vram_gb"] > vram + 0.5:
        return "too_big"
    if m["vram_gb"] + 1.0 > vram:
        return "tight"
    return "fits"


def recommended_model(hw: dict, engine: str) -> str:
    """The best voice model that runs comfortably here."""
    return "qwen3-tts-q8" if model_fit("qwen3-tts-q8", hw, engine) in ("fits", "cpu") and main_gpu(hw) else "qwen3-tts-q4"


def warnings(hw: dict, cfg: dict, engine: str) -> list[dict]:
    out = []
    g = main_gpu(hw)
    if not g:
        out.append({"level": "warn", "code": "no_gpu",
                    "message": "No dedicated graphics card found. Speech will be made on the CPU: it works, "
                               "but a 10-minute voiceover takes about 15 minutes."})
    elif g["vendor"] == "nvidia":
        major = _driver_major(g)
        if major is not None and major < 528:
            out.append({"level": "error", "code": "old_driver",
                        "message": f"Your NVIDIA driver ({g['driver']}) is too old for the engine. Update it from nvidia.com or the NVIDIA app."})
        elif major is not None and major < 580 and engine == "cuda":
            out.append({"level": "warn", "code": "driver_cuda13",
                        "message": f"Your NVIDIA driver ({g['driver']}) is older than the fastest engine needs. "
                                   "Update the driver, or use the “older driver” CUDA engine."})
    if g and g["vram_gb"] < 4:
        out.append({"level": "warn", "code": "low_vram",
                    "message": f"Your GPU has {g['vram_gb']:g} GB. Use the smaller Q4 voice model."})
    if hw["ram_gb"] < 8:
        out.append({"level": "warn", "code": "low_ram",
                    "message": f"This PC has {hw['ram_gb']:g} GB of RAM. 8 GB or more is recommended; close other apps while generating."})
    free = disk_free(cfg)
    if free is not None and free < 6 * 1024**3:
        out.append({"level": "warn", "code": "low_disk",
                    "message": f"Only {free / 1e9:.0f} GB free where models are stored. The engine and a voice model need about 3 GB."})
    if g and "laptop" in g["name"].lower() and on_battery():
        out.append({"level": "info", "code": "battery",
                    "message": "You're on battery. Plug in the charger: laptop GPUs run much slower on battery."})
    return out


def disk_free(cfg: dict) -> int | None:
    p = Path(cfg["models_dir"])
    while not p.exists() and p.parent != p:
        p = p.parent
    try:
        return shutil.disk_usage(p).free
    except OSError:
        return None
