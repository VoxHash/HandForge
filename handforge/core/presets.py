"""Built-in and user conversion presets for HandForge."""

from __future__ import annotations

from typing import Any, Dict

from .settings import load_custom_presets

# Names and options mirror the GUI preset combo (without emoji prefixes).
BUILTIN_PRESETS: Dict[str, Dict[str, Any]] = {
    "MP3 192k": {"format": "mp3", "mode": "CBR", "bitrate": "192"},
    "AAC 256k": {"format": "aac", "mode": "CBR", "bitrate": "256"},
    "FLAC Lossless": {"format": "flac", "mode": "Lossless"},
    "MP4 H.264": {
        "format": "mp4",
        "mode": "CBR",
        "video_codec": "libx264",
        "video_bitrate": "5000",
        "bitrate": "192",
    },
    "MKV H.264": {
        "format": "mkv",
        "mode": "CBR",
        "video_codec": "libx264",
        "video_bitrate": "5000",
        "bitrate": "192",
    },
    "MP4 H.265 (Smart Compression)": {
        "format": "mp4",
        "mode": "CBR",
        "video_codec": "libx265",
        "reduce_size": True,
        "use_hevc": True,
        "size_reduction_factor": 7.0,
        "bitrate": "192",
    },
    "MKV H.265 (Smart Compression)": {
        "format": "mkv",
        "mode": "CBR",
        "video_codec": "libx265",
        "reduce_size": True,
        "use_hevc": True,
        "size_reduction_factor": 7.0,
        "bitrate": "192",
    },
    "WebM VP9": {
        "format": "webm",
        "mode": "CBR",
        "video_codec": "libvpx-vp9",
        "video_quality": "30",
        "bitrate": "192",
    },
    "Extract Audio (MP3)": {
        "format": "mp3",
        "mode": "CBR",
        "bitrate": "192",
        "extract_audio_only": True,
    },
}


def normalize_preset_name(name: str) -> str:
    """Strip optional non-ASCII (emoji) prefix from a preset display name."""
    if " " in name:
        parts = name.split(" ", 1)
        first_part = parts[0]
        if first_part and not first_part.isascii():
            return parts[1]
    return name


def all_presets() -> Dict[str, Dict[str, Any]]:
    """Return built-in presets merged with user custom presets (custom wins)."""
    merged = dict(BUILTIN_PRESETS)
    merged.update(load_custom_presets())
    return merged


def get_preset(name: str) -> Dict[str, Any]:
    """Resolve a preset by name. Raises KeyError if unknown."""
    name_clean = normalize_preset_name(name)
    presets = all_presets()
    if name_clean not in presets:
        raise KeyError(name_clean)
    return dict(presets[name_clean])
