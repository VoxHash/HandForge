"""Utility modules for HandForge."""

from .errors import ActionableError, classify_error, format_actionable_error
from .ffmpeg import build_ffmpeg_cmd, run_ffmpeg, out_path
from .hwaccel import (
    detect_available_backends,
    format_detection_report,
    resolve_hw_encode,
)

__all__ = [
    "ActionableError",
    "build_ffmpeg_cmd",
    "classify_error",
    "detect_available_backends",
    "format_actionable_error",
    "format_detection_report",
    "out_path",
    "resolve_hw_encode",
    "run_ffmpeg",
]

