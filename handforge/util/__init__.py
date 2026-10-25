"""Utility modules for HandForge."""

from .analytics import (
    analytics_enabled,
    format_analytics_status,
    format_batch_summary,
)
from .audio_filters import build_audio_filter_graph, join_audio_filters
from .cloud import (
    all_cloud_roots,
    format_cloud_status,
    list_rclone_remotes,
    rclone_available,
)
from .proton_drive import (
    backup_enabled as proton_drive_backup_enabled,
    format_proton_status,
    proton_drive_available,
)
from .errors import ActionableError, classify_error, format_actionable_error
from .ffmpeg import build_ffmpeg_cmd, run_ffmpeg, out_path
from .hwaccel import (
    detect_available_backends,
    format_detection_report,
    resolve_hw_encode,
)
from .video_filters import build_video_filter_graph, join_video_filters

__all__ = [
    "ActionableError",
    "all_cloud_roots",
    "analytics_enabled",
    "build_audio_filter_graph",
    "build_ffmpeg_cmd",
    "build_video_filter_graph",
    "classify_error",
    "detect_available_backends",
    "format_actionable_error",
    "format_analytics_status",
    "format_batch_summary",
    "format_cloud_status",
    "format_detection_report",
    "format_proton_status",
    "join_audio_filters",
    "join_video_filters",
    "list_rclone_remotes",
    "out_path",
    "proton_drive_available",
    "proton_drive_backup_enabled",
    "rclone_available",
    "resolve_hw_encode",
    "run_ffmpeg",
]

