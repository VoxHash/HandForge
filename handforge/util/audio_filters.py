"""Advanced FFmpeg audio filter graph construction.

Builds real FFmpeg filter chains for EQ (``equalizer``), dynamics
(``acompressor``, ``alimiter``), and noise reduction (``afftdn``).
All advanced filters default to disabled so existing encode paths are unchanged.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Sensible defaults (FFmpeg-aligned where applicable).
DEFAULT_AUDIO_FILTER_SETTINGS: Dict[str, Any] = {
    "eq_enabled": False,
    "eq_bass": 0.0,  # dB @ ~100 Hz
    "eq_mid": 0.0,  # dB @ ~1000 Hz
    "eq_treble": 0.0,  # dB @ ~8000 Hz
    "compressor_enabled": False,
    "compressor_threshold": 0.125,  # linear (FFmpeg acompressor default)
    "compressor_ratio": 4.0,
    "compressor_attack": 20.0,  # ms
    "compressor_release": 250.0,  # ms
    "compressor_makeup": 2.0,
    "limiter_enabled": False,
    "limiter_limit": 0.95,  # linear peak ceiling
    "limiter_attack": 5.0,  # ms
    "limiter_release": 50.0,  # ms
    "denoise_enabled": False,
    "denoise_nr": 12.0,  # dB (afftdn noise_reduction)
    "denoise_nf": -50.0,  # dB (afftdn noise_floor)
    "denoise_track_noise": True,
}

# Keys copied from settings / CLI onto Job and into build_ffmpeg_cmd.
AUDIO_FILTER_SETTING_KEYS = tuple(DEFAULT_AUDIO_FILTER_SETTINGS.keys())

# 3-band EQ centre frequencies (Hz) and Q widths.
_EQ_BANDS = (
    ("eq_bass", 100.0, 0.7),
    ("eq_mid", 1000.0, 1.0),
    ("eq_treble", 8000.0, 0.7),
)


def _fmt_num(value: float) -> str:
    """Compact numeric formatting for FFmpeg filter args."""
    fval = float(value)
    if fval == int(fval):
        return str(int(fval))
    return f"{fval:g}"


def build_audio_filter_graph(
    *,
    fade_in: Optional[float] = None,
    fade_out: Optional[float] = None,
    normalize_lufs: bool = False,
    target_lufs: float = -14.0,
    eq_enabled: bool = False,
    eq_bass: float = 0.0,
    eq_mid: float = 0.0,
    eq_treble: float = 0.0,
    compressor_enabled: bool = False,
    compressor_threshold: float = 0.125,
    compressor_ratio: float = 4.0,
    compressor_attack: float = 20.0,
    compressor_release: float = 250.0,
    compressor_makeup: float = 2.0,
    limiter_enabled: bool = False,
    limiter_limit: float = 0.95,
    limiter_attack: float = 5.0,
    limiter_release: float = 50.0,
    denoise_enabled: bool = False,
    denoise_nr: float = 12.0,
    denoise_nf: float = -50.0,
    denoise_track_noise: bool = True,
) -> List[str]:
    """Return ordered FFmpeg audio filter fragments (empty when nothing enabled).

    Order: denoise → EQ → compressor → limiter → fade → loudnorm.
    """
    filters: List[str] = []

    if denoise_enabled:
        # afftdn: FFT denoise (nr / nf / optional noise-floor tracking).
        parts = [
            f"nr={_fmt_num(denoise_nr)}",
            f"nf={_fmt_num(denoise_nf)}",
        ]
        if denoise_track_noise:
            parts.append("tn=1")
        filters.append("afftdn=" + ":".join(parts))

    if eq_enabled:
        gains = {
            "eq_bass": float(eq_bass),
            "eq_mid": float(eq_mid),
            "eq_treble": float(eq_treble),
        }
        for key, freq, width_q in _EQ_BANDS:
            gain = gains[key]
            if gain == 0.0:
                continue
            filters.append(
                "equalizer="
                f"f={_fmt_num(freq)}:width_type=q:width={_fmt_num(width_q)}:"
                f"g={_fmt_num(gain)}"
            )

    if compressor_enabled:
        filters.append(
            "acompressor="
            f"threshold={_fmt_num(compressor_threshold)}:"
            f"ratio={_fmt_num(compressor_ratio)}:"
            f"attack={_fmt_num(compressor_attack)}:"
            f"release={_fmt_num(compressor_release)}:"
            f"makeup={_fmt_num(compressor_makeup)}"
        )

    if limiter_enabled:
        filters.append(
            "alimiter="
            f"limit={_fmt_num(limiter_limit)}:"
            f"attack={_fmt_num(limiter_attack)}:"
            f"release={_fmt_num(limiter_release)}:"
            "level=disabled"
        )

    if fade_in:
        filters.append(f"afade=t=in:ss=0:d={fade_in}")
    if fade_out:
        filters.append(f"afade=t=out:st=0:d={fade_out}")

    if normalize_lufs:
        filters.append(f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11")

    return filters


def join_audio_filters(filters: List[str]) -> Optional[str]:
    """Join filter fragments for ``-af``, or ``None`` if empty."""
    if not filters:
        return None
    return ",".join(filters)


def audio_filter_kwargs_from_mapping(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract advanced audio-filter kwargs from a settings/job mapping."""
    data = data or {}
    out: Dict[str, Any] = {}
    for key in AUDIO_FILTER_SETTING_KEYS:
        if key in data and data[key] is not None:
            out[key] = data[key]
        else:
            out[key] = DEFAULT_AUDIO_FILTER_SETTINGS[key]
    return out


def any_advanced_audio_filter_enabled(**kwargs: Any) -> bool:
    """True if EQ, compressor, limiter, or denoise is enabled."""
    return bool(
        kwargs.get("eq_enabled")
        or kwargs.get("compressor_enabled")
        or kwargs.get("limiter_enabled")
        or kwargs.get("denoise_enabled")
    )
