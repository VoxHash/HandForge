"""Adaptive parallel-job limits via the optional Rust native scheduler.

Loads ``libhandforge_scheduler`` (cdylib) when built; otherwise uses a pure-Python
fallback with the same decision rules so conversion still works without Rust.
"""

from __future__ import annotations

import ctypes
import os
import platform
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Keep in sync with native/handforge_scheduler/src/lib.rs
DEFAULT_JOB_RSS_MB = 350
MIN_RESERVE_MB = 768

_lib = None
_lib_checked = False
_lib_path: Optional[str] = None


class HfSystemSnapshot(ctypes.Structure):
    _fields_ = [
        ("total_mem_mb", ctypes.c_uint64),
        ("avail_mem_mb", ctypes.c_uint64),
        ("cpu_count", ctypes.c_uint32),
        ("load_x100", ctypes.c_uint32),
        ("recommended_parallel", ctypes.c_uint32),
    ]


def _candidate_lib_paths() -> list[Path]:
    """Search order for the built shared library."""
    names = {
        "Linux": "libhandforge_scheduler.so",
        "Darwin": "libhandforge_scheduler.dylib",
        "Windows": "handforge_scheduler.dll",
    }
    lib_name = names.get(platform.system(), "libhandforge_scheduler.so")
    root = Path(__file__).resolve().parents[2]
    env = os.environ.get("HANDFORGE_NATIVE_LIB")
    paths: list[Path] = []
    if env:
        paths.append(Path(env))
    paths.extend(
        [
            root / "native" / "handforge_scheduler" / "target" / "release" / lib_name,
            root / "native" / "handforge_scheduler" / "target" / "debug" / lib_name,
            Path(__file__).resolve().parent / lib_name,
        ]
    )
    return paths


def _load_native() -> Optional[ctypes.CDLL]:
    global _lib, _lib_checked, _lib_path
    if _lib_checked:
        return _lib
    _lib_checked = True
    for path in _candidate_lib_paths():
        if not path.is_file():
            continue
        try:
            lib = ctypes.CDLL(str(path))
            lib.hf_recommend_parallel.argtypes = [
                ctypes.c_uint32,
                ctypes.c_uint32,
                ctypes.c_uint64,
            ]
            lib.hf_recommend_parallel.restype = ctypes.c_uint32
            lib.hf_system_snapshot.argtypes = [
                ctypes.POINTER(HfSystemSnapshot),
                ctypes.c_uint32,
                ctypes.c_uint32,
                ctypes.c_uint64,
            ]
            lib.hf_system_snapshot.restype = ctypes.c_int32
            _lib = lib
            _lib_path = str(path)
            return _lib
        except OSError:
            continue
    _lib = None
    _lib_path = None
    return None


def native_available() -> bool:
    """True when the Rust scheduler library loaded successfully."""
    return _load_native() is not None


def native_lib_path() -> Optional[str]:
    """Path of the loaded native library, if any."""
    _load_native()
    return _lib_path


def _read_memory_mb() -> Tuple[int, int]:
    """Return (total_mb, avail_mb)."""
    if sys.platform.startswith("linux"):
        total_kb = avail_kb = free_kb = buffers_kb = cached_kb = 0
        try:
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    key, val = parts[0], int(parts[1])
                    if key == "MemTotal:":
                        total_kb = val
                    elif key == "MemAvailable:":
                        avail_kb = val
                    elif key == "MemFree:":
                        free_kb = val
                    elif key == "Buffers:":
                        buffers_kb = val
                    elif key == "Cached:":
                        cached_kb = val
            if avail_kb == 0:
                avail_kb = free_kb + buffers_kb + cached_kb
            return total_kb // 1024, avail_kb // 1024
        except OSError:
            pass
    try:
        import psutil  # optional; not a hard dependency

        vm = psutil.virtual_memory()
        return vm.total // (1024 * 1024), vm.available // (1024 * 1024)
    except Exception:
        return 8192, 4096


def _cpu_count() -> int:
    return max(1, os.cpu_count() or 1)


def _load_x100() -> int:
    if hasattr(os, "getloadavg"):
        try:
            return int(round(os.getloadavg()[0] * 100))
        except OSError:
            pass
    return 0


def recommend_parallel_from_metrics(
    user_max: int,
    active_jobs: int,
    avg_job_rss_mb: int,
    total_mem_mb: int,
    avail_mem_mb: int,
    cpu_count: int,
    load_x100: int,
) -> int:
    """Same decision rules as the Rust crate (Python fallback / tests)."""
    user_max = max(1, int(user_max))
    job_mb = DEFAULT_JOB_RSS_MB if avg_job_rss_mb <= 0 else max(64, int(avg_job_rss_mb))
    cpu = max(1, int(cpu_count))
    reserve = max(MIN_RESERVE_MB, int(total_mem_mb) // 5)
    capacity_mb = int(avail_mem_mb) + int(active_jobs) * job_mb
    usable_mb = max(0, capacity_mb - reserve)
    max_by_mem = usable_mb // job_mb
    load = load_x100 / 100.0
    cpu_cap = cpu
    if load_x100 > 0:
        if load > cpu * 0.90:
            cpu_cap = max(1, cpu // 2)
        elif load > cpu * 0.70:
            cpu_cap = max(1, int(cpu * 0.75))
    by_resource = max(1, min(max(max_by_mem, 1), cpu_cap))
    return min(user_max, by_resource)


def recommend_parallel(
    user_max: int,
    active_jobs: int = 0,
    avg_job_rss_mb: int = 0,
) -> int:
    """Return the allowed concurrent conversion count (≤ user_max)."""
    lib = _load_native()
    if lib is not None:
        return int(
            lib.hf_recommend_parallel(
                ctypes.c_uint32(max(1, user_max)),
                ctypes.c_uint32(max(0, active_jobs)),
                ctypes.c_uint64(max(0, avg_job_rss_mb)),
            )
        )
    total_mb, avail_mb = _read_memory_mb()
    return recommend_parallel_from_metrics(
        user_max,
        active_jobs,
        avg_job_rss_mb,
        total_mb,
        avail_mb,
        _cpu_count(),
        _load_x100(),
    )


def system_snapshot(
    user_max: int = 2,
    active_jobs: int = 0,
    avg_job_rss_mb: int = 0,
) -> Dict[str, Any]:
    """Memory/CPU snapshot plus recommended parallel count."""
    lib = _load_native()
    if lib is not None:
        snap = HfSystemSnapshot()
        rc = lib.hf_system_snapshot(
            ctypes.byref(snap),
            ctypes.c_uint32(max(1, user_max)),
            ctypes.c_uint32(max(0, active_jobs)),
            ctypes.c_uint64(max(0, avg_job_rss_mb)),
        )
        if rc == 0:
            return {
                "backend": "rust",
                "lib_path": _lib_path,
                "total_mem_mb": int(snap.total_mem_mb),
                "avail_mem_mb": int(snap.avail_mem_mb),
                "cpu_count": int(snap.cpu_count),
                "load_x100": int(snap.load_x100),
                "recommended_parallel": int(snap.recommended_parallel),
            }
    total_mb, avail_mb = _read_memory_mb()
    cpu = _cpu_count()
    load = _load_x100()
    rec = recommend_parallel_from_metrics(
        user_max, active_jobs, avg_job_rss_mb, total_mb, avail_mb, cpu, load
    )
    return {
        "backend": "python",
        "lib_path": None,
        "total_mem_mb": total_mb,
        "avail_mem_mb": avail_mb,
        "cpu_count": cpu,
        "load_x100": load,
        "recommended_parallel": rec,
    }


def estimate_job_rss_mb(is_video: bool = False) -> int:
    """Rough per-job RSS used when adapting the pool (MiB)."""
    return 500 if is_video else 180
