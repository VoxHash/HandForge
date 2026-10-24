"""Settings management for HandForge."""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional


def get_config_dir() -> Path:
    """Get the configuration directory."""
    if os.name == "nt":  # Windows
        config_dir = Path(os.environ.get("APPDATA", Path.home())) / ".handforge"
    else:  # Linux/macOS
        config_dir = Path.home() / ".handforge"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def load_json_file(filename: str, default: Any = None) -> Any:
    """Load a JSON file from config directory."""
    config_dir = get_config_dir()
    filepath = config_dir / filename
    
    if not filepath.exists():
        return default if default is not None else {}
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default if default is not None else {}


def save_json_file(filename: str, data: Any) -> None:
    """Save data to a JSON file in config directory."""
    config_dir = get_config_dir()
    filepath = config_dir / filename
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        raise IOError(f"Failed to save {filename}: {e}")


def load_settings() -> Dict[str, Any]:
    """Load application settings."""
    defaults = {
        "parallel": 2,
        # Cap concurrent jobs from free RAM / load (Rust native when built).
        "adaptive_parallel": True,
        "dark_theme": False,
        "prefer_external_cover": False,
        "dup_handling": "Overwrite",
        "on_exists": "overwrite",
        "normalize_lufs": False,
        "target_lufs": -14.0,
        # Advanced audio filters (disabled by default — see util/audio_filters.py)
        "eq_enabled": False,
        "eq_bass": 0.0,
        "eq_mid": 0.0,
        "eq_treble": 0.0,
        "compressor_enabled": False,
        "compressor_threshold": 0.125,
        "compressor_ratio": 4.0,
        "compressor_attack": 20.0,
        "compressor_release": 250.0,
        "compressor_makeup": 2.0,
        "limiter_enabled": False,
        "limiter_limit": 0.95,
        "limiter_attack": 5.0,
        "limiter_release": 50.0,
        "denoise_enabled": False,
        "denoise_nr": 12.0,
        "denoise_nf": -50.0,
        "denoise_track_noise": True,
        "delete_original": False,  # Delete original file after conversion
        "codec_threads": {
            "mp3": 1,
            "aac": 1,
            "m4a": 1,
            "flac": 1,
            "wav": 1,
        },
        "ewma_alpha": 0.3,
        "auto_retry_enabled": True,
        "auto_retry_patterns": [
            "Error while decoding",
            "Invalid data found",
            "could not find codec parameters",
        ],
        "minimize_to_tray": True,
        "output_dir": None,  # None = use default
        "default_video_quality": "medium",
        "default_video_codec": "libx264",
        "default_reduction_factor": 7.0,
        "default_two_pass": False,
        # Video HW acceleration: auto | software | nvenc | qsv | vaapi | videotoolbox
        "hw_accel": "auto",
        "language": None,  # None = auto-detect, or locale code like 'en', 'ru', etc.
    }
    
    settings = load_json_file("settings.json", {})
    # Merge with defaults
    for key, value in defaults.items():
        if key not in settings:
            settings[key] = value
    
    return settings


def save_settings(settings: Dict[str, Any]) -> None:
    """Save application settings."""
    save_json_file("settings.json", settings)


def load_custom_presets() -> Dict[str, Dict[str, Any]]:
    """Load custom conversion presets."""
    return load_json_file("presets.json", {})


def save_custom_presets(presets: Dict[str, Dict[str, Any]]) -> None:
    """Save custom conversion presets."""
    save_json_file("presets.json", presets)


def load_patterns() -> List[str]:
    """Load filename patterns for metadata parsing."""
    patterns = load_json_file("patterns.json", [])
    if not patterns:
        # Default patterns
        patterns = [
            "{artist} - {title}",
            "{track} - {artist} - {title}",
            "{album} - {artist} - {title}",
        ]
    return patterns


def save_patterns(patterns: List[str]) -> None:
    """Save filename patterns."""
    save_json_file("patterns.json", patterns)


def load_autoretry() -> Dict[str, Any]:
    """Load auto-retry rules."""
    defaults = {
        "enabled": True,
        "patterns": [
            "Error while decoding",
            "Invalid data found",
            "could not find codec parameters",
        ],
    }
    return load_json_file("autoretry.json", defaults)


def save_autoretry(autoretry: Dict[str, Any]) -> None:
    """Save auto-retry rules."""
    save_json_file("autoretry.json", autoretry)


def load_seen_files() -> Dict[str, Any]:
    """Load seen files cache."""
    return load_json_file("seen_files.json", {})


def save_seen_files(seen_files: Dict[str, Any]) -> None:
    """Save seen files cache."""
    save_json_file("seen_files.json", seen_files)

