"""Hardware-accelerated video encoder detection and selection.

Probes the local FFmpeg build and (optionally) runs a short encode to verify
NVENC, Quick Sync, VAAPI, and VideoToolbox actually work — not just that the
encoder name is listed.
"""

from __future__ import annotations

import os
import platform
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .ffmpeg import find_ffmpeg

# User-facing preference values (settings / CLI / Preferences).
HW_PREF_AUTO = "auto"
HW_PREF_SOFTWARE = "software"
HW_PREF_NVENC = "nvenc"
HW_PREF_QSV = "qsv"
HW_PREF_VAAPI = "vaapi"
HW_PREF_VIDEOTOOLBOX = "videotoolbox"

HW_PREFERENCES: Tuple[str, ...] = (
    HW_PREF_AUTO,
    HW_PREF_SOFTWARE,
    HW_PREF_NVENC,
    HW_PREF_QSV,
    HW_PREF_VAAPI,
    HW_PREF_VIDEOTOOLBOX,
)

# Auto-detect preference order (first working backend wins).
_AUTO_ORDER: Tuple[str, ...] = (
    HW_PREF_NVENC,
    HW_PREF_QSV,
    HW_PREF_VAAPI,
    HW_PREF_VIDEOTOOLBOX,
)

_FAMILY_ENCODERS: Dict[str, Dict[str, str]] = {
    HW_PREF_NVENC: {"h264": "h264_nvenc", "hevc": "hevc_nvenc"},
    HW_PREF_QSV: {"h264": "h264_qsv", "hevc": "hevc_qsv"},
    HW_PREF_VAAPI: {"h264": "h264_vaapi", "hevc": "hevc_vaapi"},
    HW_PREF_VIDEOTOOLBOX: {
        "h264": "h264_videotoolbox",
        "hevc": "hevc_videotoolbox",
    },
}

_SOFTWARE_BY_FAMILY = {"h264": "libx264", "hevc": "libx265"}

_HW_ENCODER_NAMES = frozenset(
    enc for mapping in _FAMILY_ENCODERS.values() for enc in mapping.values()
)

# Cache: (ffmpeg_path, mtime_ns) -> detection result
_detect_cache: Dict[Tuple[str, int], Dict[str, Any]] = {}


@dataclass
class HwEncodePlan:
    """Resolved encoder + FFmpeg args for one video encode."""

    backend: str
    encoder: str
    family: str  # h264 | hevc | other
    # Global options inserted before -i (e.g. -init_hw_device).
    pre_input_args: List[str] = field(default_factory=list)
    # Extra -vf filter pieces (joined with existing filters).
    vf_filters: List[str] = field(default_factory=list)
    # Device path when backend is vaapi (for logging / retry).
    vaapi_device: Optional[str] = None
    used_hw: bool = False

    def software_fallback_encoder(self) -> str:
        return _SOFTWARE_BY_FAMILY.get(self.family, "libx264")


def normalize_hw_preference(value: Optional[str]) -> str:
    """Normalize a preference string; unknown values become auto."""
    if not value:
        return HW_PREF_AUTO
    key = str(value).strip().lower()
    aliases = {
        "sw": HW_PREF_SOFTWARE,
        "cpu": HW_PREF_SOFTWARE,
        "none": HW_PREF_SOFTWARE,
        "quicksync": HW_PREF_QSV,
        "quick_sync": HW_PREF_QSV,
        "intel": HW_PREF_QSV,
        "nvidia": HW_PREF_NVENC,
        "cuda": HW_PREF_NVENC,
        "vt": HW_PREF_VIDEOTOOLBOX,
        "videotoolbox": HW_PREF_VIDEOTOOLBOX,
        "macos": HW_PREF_VIDEOTOOLBOX,
    }
    key = aliases.get(key, key)
    if key in HW_PREFERENCES:
        return key
    return HW_PREF_AUTO


def codec_family(codec: Optional[str]) -> Optional[str]:
    """Map a codec name to h264/hevc family, or None if not HW-mappable."""
    if not codec:
        return "h264"
    name = codec.lower().strip()
    if name in ("libx264", "h264", "avc") or name.startswith("h264_"):
        return "h264"
    if name in ("libx265", "hevc", "h265") or name.startswith("hevc_"):
        return "hevc"
    return None


def is_hw_encoder(codec: Optional[str]) -> bool:
    """Return True if codec is a known hardware encoder name."""
    if not codec:
        return False
    return codec.lower().strip() in _HW_ENCODER_NAMES


def software_fallback_codec(codec: Optional[str]) -> str:
    """Software encoder for a HW (or software) codec name."""
    family = codec_family(codec)
    if family:
        return _SOFTWARE_BY_FAMILY[family]
    return "libx264"


def list_compiled_encoders(ffmpeg: Optional[str] = None) -> Set[str]:
    """Return encoder names reported by `ffmpeg -encoders`."""
    ffmpeg = ffmpeg or find_ffmpeg()
    if not ffmpeg:
        return set()
    try:
        result = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    # FFmpeg prints encoders on stdout (some builds mix stderr).
    text = (result.stdout or "") + "\n" + (result.stderr or "")
    names: Set[str] = set()
    for line in text.splitlines():
        # Lines look like: " V....D h264_nvenc           NVIDIA NVENC ..."
        stripped = line.strip()
        if len(stripped) < 10 or stripped.startswith("Encoders") or stripped.startswith("---"):
            continue
        # Flags then name
        parts = stripped.split()
        if len(parts) >= 2 and parts[0][0] in "VASD":
            names.add(parts[1])
    return names


def _run_probe(cmd: Sequence[str], timeout: float = 20.0) -> bool:
    try:
        result = subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _probe_size() -> str:
    # NVENC rejects very small frames; 320x240 is safely above the minimum.
    return "320x240"


def probe_encoder(
    encoder: str,
    *,
    backend: str,
    ffmpeg: Optional[str] = None,
    vaapi_device: Optional[str] = None,
) -> bool:
    """Run a short lavfi encode to verify the encoder works on this host."""
    ffmpeg = ffmpeg or find_ffmpeg()
    if not ffmpeg:
        return False

    size = _probe_size()
    lavfi = f"testsrc=size={size}:rate=30"
    base_tail = [
        "-f",
        "lavfi",
        "-i",
        lavfi,
        "-t",
        "0.3",
        "-an",
        "-c:v",
        encoder,
        "-f",
        "null",
        "-",
    ]

    if backend == HW_PREF_VAAPI:
        device = vaapi_device or find_vaapi_device(ffmpeg=ffmpeg)
        if not device:
            return False
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-init_hw_device",
            f"vaapi=va:{device}",
            "-filter_hw_device",
            "va",
            *base_tail[:4],  # -f lavfi -i ...
            "-vf",
            "format=nv12,hwupload",
            *base_tail[4:],
        ]
        return _run_probe(cmd)

    if backend == HW_PREF_QSV:
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-init_hw_device",
            "qsv=hw",
            "-filter_hw_device",
            "hw",
            *base_tail[:4],
            "-vf",
            "format=nv12,hwupload=extra_hw_frames=64",
            *base_tail[4:],
        ]
        # Some builds work without explicit init — try with init first, then bare.
        if _run_probe(cmd):
            return True
        bare = [ffmpeg, "-hide_banner", "-y", *base_tail]
        return _run_probe(bare)

    # NVENC / VideoToolbox: software frames → HW encoder is fine.
    cmd = [ffmpeg, "-hide_banner", "-y", *base_tail]
    if backend == HW_PREF_NVENC:
        # Prefer yuv420p to avoid odd pixel formats from testsrc.
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-y",
            *base_tail[:4],
            "-pix_fmt",
            "yuv420p",
            *base_tail[4:],
        ]
    return _run_probe(cmd)


def _candidate_vaapi_devices() -> List[str]:
    devices: List[str] = []
    dri = "/dev/dri"
    if not os.path.isdir(dri):
        return devices
    # Prefer by-path ordering: try AMD/Intel render nodes; include all renderD*.
    try:
        for name in sorted(os.listdir(dri)):
            if name.startswith("renderD"):
                devices.append(os.path.join(dri, name))
    except OSError:
        pass
    return devices


def find_vaapi_device(*, ffmpeg: Optional[str] = None) -> Optional[str]:
    """Return a render node that can open VAAPI, or None."""
    ffmpeg = ffmpeg or find_ffmpeg()
    if not ffmpeg:
        return None
    for device in _candidate_vaapi_devices():
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-init_hw_device",
            f"vaapi=va:{device}",
            "-filter_hw_device",
            "va",
            "-f",
            "lavfi",
            "-i",
            f"testsrc=size={_probe_size()}:rate=30",
            "-t",
            "0.2",
            "-vf",
            "format=nv12,hwupload",
            "-c:v",
            "h264_vaapi",
            "-f",
            "null",
            "-",
        ]
        if _run_probe(cmd):
            return device
    return None


def detect_available_backends(
    *,
    probe: bool = True,
    force_refresh: bool = False,
    ffmpeg: Optional[str] = None,
) -> Dict[str, Any]:
    """Detect which HW backends are usable.

    Returns a dict::

        {
          "ffmpeg": "/usr/bin/ffmpeg",
          "compiled": {"h264_nvenc": True, ...},
          "backends": {"nvenc": True, "qsv": False, "vaapi": True, "videotoolbox": False},
          "encoders": {"nvenc": {"h264": "h264_nvenc", ...}, ...},
          "vaapi_device": "/dev/dri/renderD129" | None,
          "probed": True,
        }
    """
    ffmpeg = ffmpeg or find_ffmpeg()
    empty: Dict[str, Any] = {
        "ffmpeg": ffmpeg,
        "compiled": {},
        "backends": {
            HW_PREF_NVENC: False,
            HW_PREF_QSV: False,
            HW_PREF_VAAPI: False,
            HW_PREF_VIDEOTOOLBOX: False,
        },
        "encoders": {},
        "vaapi_device": None,
        "probed": probe,
    }
    if not ffmpeg:
        return empty

    try:
        mtime_ns = os.stat(ffmpeg).st_mtime_ns
    except OSError:
        mtime_ns = 0
    cache_key = (ffmpeg, mtime_ns, bool(probe))
    # Use string key for typed cache
    str_key = (f"{ffmpeg}|{mtime_ns}|{int(probe)}", 0)
    if not force_refresh and str_key in _detect_cache:
        return dict(_detect_cache[str_key])

    compiled = list_compiled_encoders(ffmpeg)
    compiled_map = {name: name in compiled for name in _HW_ENCODER_NAMES}

    backends = {
        HW_PREF_NVENC: False,
        HW_PREF_QSV: False,
        HW_PREF_VAAPI: False,
        HW_PREF_VIDEOTOOLBOX: False,
    }
    encoders: Dict[str, Dict[str, str]] = {}
    vaapi_device: Optional[str] = None

    is_macos = platform.system() == "Darwin"

    for backend, family_map in _FAMILY_ENCODERS.items():
        if backend == HW_PREF_VIDEOTOOLBOX and not is_macos:
            # Still report compiled status, but do not mark available off-macOS.
            if any(enc in compiled for enc in family_map.values()):
                encoders[backend] = {
                    fam: enc for fam, enc in family_map.items() if enc in compiled
                }
            continue

        available_families = {
            fam: enc for fam, enc in family_map.items() if enc in compiled
        }
        if not available_families:
            continue

        ok = False
        if not probe:
            ok = True
            if backend == HW_PREF_VAAPI:
                vaapi_device = next(iter(_candidate_vaapi_devices()), None)
        else:
            # Prefer probing h264; fall back to hevc if only hevc is compiled.
            probe_family = "h264" if "h264" in available_families else next(
                iter(available_families)
            )
            probe_enc = available_families[probe_family]
            if backend == HW_PREF_VAAPI:
                vaapi_device = find_vaapi_device(ffmpeg=ffmpeg)
                ok = bool(vaapi_device) and probe_encoder(
                    probe_enc,
                    backend=backend,
                    ffmpeg=ffmpeg,
                    vaapi_device=vaapi_device,
                )
                # If h264 probe used find_vaapi_device already, device is set.
                if ok and "hevc" in available_families:
                    # Keep hevc listed only if it also probes (optional).
                    if not probe_encoder(
                        available_families["hevc"],
                        backend=backend,
                        ffmpeg=ffmpeg,
                        vaapi_device=vaapi_device,
                    ):
                        available_families = {
                            k: v for k, v in available_families.items() if k != "hevc"
                        }
            else:
                ok = probe_encoder(
                    probe_enc, backend=backend, ffmpeg=ffmpeg
                )

        if ok and available_families:
            backends[backend] = True
            encoders[backend] = available_families

    result: Dict[str, Any] = {
        "ffmpeg": ffmpeg,
        "compiled": compiled_map,
        "backends": backends,
        "encoders": encoders,
        "vaapi_device": vaapi_device,
        "probed": probe,
    }
    _detect_cache[str_key] = dict(result)
    return result


def clear_detection_cache() -> None:
    """Clear cached detection results (for tests)."""
    _detect_cache.clear()


def resolve_hw_encode(
    preference: Optional[str],
    *,
    software_codec: Optional[str] = "libx264",
    detection: Optional[Dict[str, Any]] = None,
    force_software: bool = False,
) -> HwEncodePlan:
    """Choose an encoder plan from preference + detection.

    ``software_codec`` is the intended software encoder (libx264 / libx265) or
    an already-selected codec. Non-H.264/H.265 codecs are left unchanged.
    """
    pref = normalize_hw_preference(preference)
    family = codec_family(software_codec)
    soft = (
        _SOFTWARE_BY_FAMILY.get(family, software_codec or "libx264")
        if family
        else (software_codec or "libx264")
    )

    if force_software or pref == HW_PREF_SOFTWARE or family is None:
        return HwEncodePlan(
            backend=HW_PREF_SOFTWARE,
            encoder=soft if family else (software_codec or "libx264"),
            family=family or "other",
            used_hw=False,
        )

    # Explicit HW codec already requested as software_codec / video_codec.
    if is_hw_encoder(software_codec):
        backend = _backend_for_encoder(software_codec or "")
        plan = _plan_for_backend(
            backend,
            family or "h264",
            detection=detection,
            encoder_override=software_codec,
        )
        if plan:
            return plan
        return HwEncodePlan(
            backend=HW_PREF_SOFTWARE,
            encoder=software_fallback_codec(software_codec),
            family=family or "h264",
            used_hw=False,
        )

    info = detection if detection is not None else detect_available_backends(probe=True)
    backends: Dict[str, bool] = info.get("backends") or {}

    candidates: List[str]
    if pref == HW_PREF_AUTO:
        candidates = [b for b in _AUTO_ORDER if backends.get(b)]
    else:
        candidates = [pref] if backends.get(pref) else []

    for backend in candidates:
        plan = _plan_for_backend(backend, family, detection=info)
        if plan:
            return plan

    return HwEncodePlan(
        backend=HW_PREF_SOFTWARE,
        encoder=soft,
        family=family,
        used_hw=False,
    )


def _backend_for_encoder(encoder: str) -> str:
    name = encoder.lower()
    for backend, mapping in _FAMILY_ENCODERS.items():
        if name in mapping.values():
            return backend
    return HW_PREF_SOFTWARE


def _plan_for_backend(
    backend: str,
    family: str,
    *,
    detection: Optional[Dict[str, Any]] = None,
    encoder_override: Optional[str] = None,
) -> Optional[HwEncodePlan]:
    info = detection or {}
    enc_map = (info.get("encoders") or {}).get(backend) or _FAMILY_ENCODERS.get(
        backend, {}
    )
    encoder = encoder_override or enc_map.get(family)
    if not encoder:
        return None

    pre: List[str] = []
    vfs: List[str] = []
    vaapi_device = info.get("vaapi_device")

    if backend == HW_PREF_VAAPI:
        if not vaapi_device:
            vaapi_device = find_vaapi_device()
        if not vaapi_device:
            return None
        pre = [
            "-init_hw_device",
            f"vaapi=va:{vaapi_device}",
            "-filter_hw_device",
            "va",
        ]
        vfs = ["format=nv12", "hwupload"]
    elif backend == HW_PREF_QSV:
        pre = ["-init_hw_device", "qsv=hw", "-filter_hw_device", "hw"]
        vfs = ["format=nv12", "hwupload=extra_hw_frames=64"]

    return HwEncodePlan(
        backend=backend,
        encoder=encoder,
        family=family,
        pre_input_args=pre,
        vf_filters=vfs,
        vaapi_device=vaapi_device,
        used_hw=True,
    )


def apply_hw_rate_control(
    cmd: List[str],
    *,
    encoder: str,
    video_bitrate: Optional[str] = None,
    video_quality: Optional[str] = None,
    crf_value: Optional[str] = None,
    preset: Optional[str] = None,
) -> None:
    """Append rate-control / preset flags appropriate for a HW or SW encoder.

    Mutates ``cmd`` in place. Call after ``-c:v`` has been set.
    """
    enc = encoder.lower()
    quality = video_quality or crf_value

    if enc in ("libx264", "libx265"):
        if video_bitrate:
            cmd.extend(["-b:v", f"{video_bitrate}k"])
        elif quality:
            cmd.extend(["-crf", str(quality)])
        if preset:
            cmd.extend(["-preset", preset])
        return

    if enc.endswith("_nvenc"):
        if video_bitrate:
            cmd.extend(["-b:v", f"{video_bitrate}k"])
        elif quality:
            cmd.extend(["-rc", "constqp", "-qp", str(quality)])
        else:
            cmd.extend(["-rc", "constqp", "-qp", "23"])
        nv_preset = _map_nvenc_preset(preset)
        cmd.extend(["-preset", nv_preset])
        return

    if enc.endswith("_qsv"):
        if video_bitrate:
            cmd.extend(["-b:v", f"{video_bitrate}k"])
        elif quality:
            cmd.extend(["-global_quality", str(quality)])
        else:
            cmd.extend(["-global_quality", "23"])
        return

    if enc.endswith("_vaapi"):
        if video_bitrate:
            cmd.extend(["-b:v", f"{video_bitrate}k"])
        elif quality:
            cmd.extend(["-qp", str(quality)])
        else:
            cmd.extend(["-qp", "23"])
        return

    if enc.endswith("_videotoolbox"):
        if video_bitrate:
            cmd.extend(["-b:v", f"{video_bitrate}k"])
        elif quality:
            # VideoToolbox uses 1–100 scale; map CRF-ish 18–32 → ~65–40.
            try:
                crf = float(quality)
                qv = max(1, min(100, int(100 - (crf - 18) * (60 / 14))))
            except (TypeError, ValueError):
                qv = 65
            cmd.extend(["-q:v", str(qv)])
        else:
            cmd.extend(["-b:v", "5M"])
        return

    if video_bitrate:
        cmd.extend(["-b:v", f"{video_bitrate}k"])


def _map_nvenc_preset(preset: Optional[str]) -> str:
    if not preset:
        return "p4"
    p = preset.lower()
    mapping = {
        "ultrafast": "p1",
        "superfast": "p1",
        "veryfast": "p2",
        "faster": "p3",
        "fast": "p3",
        "medium": "p4",
        "slow": "p5",
        "slower": "p6",
        "veryslow": "p7",
        "p1": "p1",
        "p2": "p2",
        "p3": "p3",
        "p4": "p4",
        "p5": "p5",
        "p6": "p6",
        "p7": "p7",
    }
    return mapping.get(p, "p4")


def format_detection_report(info: Optional[Dict[str, Any]] = None) -> str:
    """Human-readable detection summary for CLI / logs."""
    info = info if info is not None else detect_available_backends(probe=True)
    lines = [
        f"FFmpeg: {info.get('ffmpeg') or '(not found)'}",
        f"Probed: {info.get('probed', False)}",
    ]
    backends = info.get("backends") or {}
    encoders = info.get("encoders") or {}
    for name in (HW_PREF_NVENC, HW_PREF_QSV, HW_PREF_VAAPI, HW_PREF_VIDEOTOOLBOX):
        ok = backends.get(name, False)
        status = "available" if ok else "unavailable"
        detail = ""
        if ok and name in encoders:
            detail = " (" + ", ".join(
                f"{fam}={enc}" for fam, enc in encoders[name].items()
            ) + ")"
        if name == HW_PREF_VAAPI and info.get("vaapi_device"):
            detail += f" device={info['vaapi_device']}"
        lines.append(f"  {name}: {status}{detail}")
    return "\n".join(lines)


def looks_like_hw_failure(stderr: str) -> bool:
    """Heuristic: stderr suggests the HW encoder path failed."""
    if not stderr:
        return True
    text = stderr.lower()
    needles = (
        "nvenc",
        "cuda",
        "vaapi",
        "qsv",
        "quick sync",
        "videotoolbox",
        "cannot load libcuda",
        "no nvenc capable devices",
        "failed to initialise vaapi",
        "device creation failed",
        "error while opening encoder",
        "initializeencoder failed",
        "function not implemented",
        "openencodesession",
        "openencode session",
    )
    return any(n in text for n in needles)
