"""Advanced FFmpeg video filter graph construction.

Builds real FFmpeg filter chains for color (`eq`: brightness / contrast /
saturation) and single-pass stabilization (`deshake`).

Stabilization uses ``deshake`` (single encode pass) so it composes with the
existing software → HW-upload filter path. Multi-pass ``vidstabdetect`` /
``vidstabtransform`` is not used here — it needs a separate analysis pass and
temp files; ``deshake`` is the practical default with milder shake correction.

All advanced filters default to disabled so existing encode paths are unchanged.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Sensible defaults (FFmpeg-aligned where applicable).
DEFAULT_VIDEO_FILTER_SETTINGS: Dict[str, Any] = {
    "video_color_enabled": False,
    "video_brightness": 0.0,  # eq brightness (−1.0 … 1.0)
    "video_contrast": 1.0,  # eq contrast (typically 0.0 … 2.0)
    "video_saturation": 1.0,  # eq saturation (0.0 … 3.0)
    "video_stabilize_enabled": False,
    "video_stabilize_rx": 16,  # deshake search range X (0–64)
    "video_stabilize_ry": 16,  # deshake search range Y (0–64)
    "video_stabilize_edge": "mirror",  # blank | original | clamp | mirror
}

VIDEO_FILTER_SETTING_KEYS = tuple(DEFAULT_VIDEO_FILTER_SETTINGS.keys())

_EDGE_MODES = frozenset({"blank", "original", "clamp", "mirror"})

# Identity values for eq — skip filter when enabled but unchanged.
_EQ_IDENTITY = {
    "video_brightness": 0.0,
    "video_contrast": 1.0,
    "video_saturation": 1.0,
}


def _fmt_num(value: float) -> str:
    """Compact numeric formatting for FFmpeg filter args."""
    fval = float(value)
    if fval == int(fval):
        return str(int(fval))
    return f"{fval:g}"


def _snap_deshake_range(value: int) -> int:
    """Clamp to 0–64 and snap to a multiple of 16 (FFmpeg deshake rule).

    Midpoints round up (e.g. 8 → 16) so small non-zero ranges stay useful.
    """
    n = max(0, min(64, int(value)))
    if n == 0:
        return 0
    snapped = ((n + 8) // 16) * 16
    return max(16, min(64, snapped))


def build_video_filter_graph(
    *,
    video_color_enabled: bool = False,
    video_brightness: float = 0.0,
    video_contrast: float = 1.0,
    video_saturation: float = 1.0,
    video_stabilize_enabled: bool = False,
    video_stabilize_rx: int = 16,
    video_stabilize_ry: int = 16,
    video_stabilize_edge: str = "mirror",
) -> List[str]:
    """Return ordered FFmpeg video filter fragments (empty when nothing enabled).

    Order: deshake (stabilize) → eq (color). Callers prepend/append crop, scale,
    and HW upload filters around this list.
    """
    filters: List[str] = []

    if video_stabilize_enabled:
        edge = str(video_stabilize_edge or "mirror").lower()
        if edge not in _EDGE_MODES:
            edge = "mirror"
        # FFmpeg deshake requires rx/ry to be multiples of 16 (0–64).
        rx = _snap_deshake_range(video_stabilize_rx)
        ry = _snap_deshake_range(video_stabilize_ry)
        filters.append(
            "deshake="
            f"rx={rx}:ry={ry}:edge={edge}"
        )

    if video_color_enabled:
        brightness = float(video_brightness)
        contrast = float(video_contrast)
        saturation = float(video_saturation)
        if not (
            brightness == _EQ_IDENTITY["video_brightness"]
            and contrast == _EQ_IDENTITY["video_contrast"]
            and saturation == _EQ_IDENTITY["video_saturation"]
        ):
            filters.append(
                "eq="
                f"brightness={_fmt_num(brightness)}:"
                f"contrast={_fmt_num(contrast)}:"
                f"saturation={_fmt_num(saturation)}"
            )

    return filters


def join_video_filters(filters: List[str]) -> Optional[str]:
    """Join filter fragments for ``-vf``, or ``None`` if empty."""
    if not filters:
        return None
    return ",".join(filters)


def video_filter_kwargs_from_mapping(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract advanced video-filter kwargs from a settings/job mapping."""
    data = data or {}
    out: Dict[str, Any] = {}
    for key in VIDEO_FILTER_SETTING_KEYS:
        if key in data and data[key] is not None:
            out[key] = data[key]
        else:
            out[key] = DEFAULT_VIDEO_FILTER_SETTINGS[key]
    return out


def any_advanced_video_filter_enabled(**kwargs: Any) -> bool:
    """True if color adjust or stabilize is enabled."""
    return bool(
        kwargs.get("video_color_enabled") or kwargs.get("video_stabilize_enabled")
    )
