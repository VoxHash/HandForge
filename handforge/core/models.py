"""Data models for HandForge."""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class Job:
    """Represents a conversion job."""
    
    src: str
    dst_dir: str
    format: str
    mode: str = "CBR"  # CBR, VBR, Lossless
    bitrate: Optional[str] = None
    vbrq: Optional[str] = None
    sample_rate: Optional[str] = None
    channels: Optional[str] = None
    meta_title: Optional[str] = None
    meta_artist: Optional[str] = None
    meta_album: Optional[str] = None
    meta_year: Optional[str] = None
    meta_genre: Optional[str] = None
    meta_track: Optional[str] = None
    copy_meta: bool = True
    strip_meta: bool = False
    prefer_external_cover: bool = False
    normalize_lufs: bool = False
    target_lufs: float = -14.0
    # Advanced audio filters (FFmpeg equalizer / acompressor / alimiter / afftdn)
    eq_enabled: bool = False
    eq_bass: float = 0.0
    eq_mid: float = 0.0
    eq_treble: float = 0.0
    compressor_enabled: bool = False
    compressor_threshold: float = 0.125
    compressor_ratio: float = 4.0
    compressor_attack: float = 20.0
    compressor_release: float = 250.0
    compressor_makeup: float = 2.0
    limiter_enabled: bool = False
    limiter_limit: float = 0.95
    limiter_attack: float = 5.0
    limiter_release: float = 50.0
    denoise_enabled: bool = False
    denoise_nr: float = 12.0
    denoise_nf: float = -50.0
    denoise_track_noise: bool = True
    threads: int = 1
    custom_args: Optional[str] = None
    # Video conversion options
    video_codec: Optional[str] = None
    video_bitrate: Optional[str] = None
    video_quality: Optional[str] = None
    resolution: Optional[str] = None  # e.g., "1920x1080", "1280x720"
    fps: Optional[str] = None
    extract_audio_only: bool = False  # Extract audio from video
    # Video size reduction options
    reduce_size: bool = False  # Enable smart size reduction
    size_reduction_factor: Optional[float] = None  # Target reduction (e.g., 5.0 for 5x reduction)
    use_hevc: bool = False  # Use H.265/HEVC for better compression
    two_pass: bool = False  # Use two-pass encoding for optimal quality/size
    # Subtitle options
    subtitle_track: Optional[int] = None  # Subtitle track index to include (None = no subtitles, -1 = all)
    # Audio trimming
    trim_start: Optional[float] = None  # Start time in seconds
    trim_end: Optional[float] = None  # End time in seconds
    # Audio effects
    fade_in: Optional[float] = None  # Fade in duration in seconds
    fade_out: Optional[float] = None  # Fade out duration in seconds
    # Video trimming
    video_trim_start: Optional[float] = None  # Video start time in seconds
    video_trim_end: Optional[float] = None  # Video end time in seconds
    # Video cropping
    crop_x: Optional[int] = None  # Crop X offset
    crop_y: Optional[int] = None  # Crop Y offset
    crop_width: Optional[int] = None  # Crop width
    crop_height: Optional[int] = None  # Crop height
    # Video quality preset
    video_quality_preset: Optional[str] = None  # low, medium, high, ultra
    # Multiple audio tracks
    audio_track: Optional[int] = None  # Audio track index to use (None = first/default)
    # Hardware acceleration preference (None = use settings["hw_accel"])
    hw_accel: Optional[str] = None  # auto | software | nvenc | qsv | vaapi | videotoolbox
    # File management
    delete_original: bool = False  # Delete original file after successful conversion
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            "src": self.src,
            "dst_dir": self.dst_dir,
            "format": self.format,
            "mode": self.mode,
            "bitrate": self.bitrate,
            "vbrq": self.vbrq,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "meta_title": self.meta_title,
            "meta_artist": self.meta_artist,
            "meta_album": self.meta_album,
            "meta_year": self.meta_year,
            "meta_genre": self.meta_genre,
            "meta_track": self.meta_track,
            "copy_meta": self.copy_meta,
            "strip_meta": self.strip_meta,
            "prefer_external_cover": self.prefer_external_cover,
            "normalize_lufs": self.normalize_lufs,
            "target_lufs": self.target_lufs,
            "eq_enabled": self.eq_enabled,
            "eq_bass": self.eq_bass,
            "eq_mid": self.eq_mid,
            "eq_treble": self.eq_treble,
            "compressor_enabled": self.compressor_enabled,
            "compressor_threshold": self.compressor_threshold,
            "compressor_ratio": self.compressor_ratio,
            "compressor_attack": self.compressor_attack,
            "compressor_release": self.compressor_release,
            "compressor_makeup": self.compressor_makeup,
            "limiter_enabled": self.limiter_enabled,
            "limiter_limit": self.limiter_limit,
            "limiter_attack": self.limiter_attack,
            "limiter_release": self.limiter_release,
            "denoise_enabled": self.denoise_enabled,
            "denoise_nr": self.denoise_nr,
            "denoise_nf": self.denoise_nf,
            "denoise_track_noise": self.denoise_track_noise,
            "threads": self.threads,
            "custom_args": self.custom_args,
            "video_codec": self.video_codec,
            "video_bitrate": self.video_bitrate,
            "video_quality": self.video_quality,
            "resolution": self.resolution,
            "fps": self.fps,
            "extract_audio_only": self.extract_audio_only,
            "reduce_size": self.reduce_size,
            "size_reduction_factor": self.size_reduction_factor,
            "use_hevc": self.use_hevc,
            "two_pass": self.two_pass,
            "subtitle_track": self.subtitle_track,
            "trim_start": self.trim_start,
            "trim_end": self.trim_end,
            "fade_in": self.fade_in,
            "fade_out": self.fade_out,
            "video_trim_start": self.video_trim_start,
            "video_trim_end": self.video_trim_end,
            "crop_x": self.crop_x,
            "crop_y": self.crop_y,
            "crop_width": self.crop_width,
            "crop_height": self.crop_height,
            "video_quality_preset": self.video_quality_preset,
            "audio_track": self.audio_track,
            "hw_accel": self.hw_accel,
            "delete_original": self.delete_original,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        """Create job from dictionary."""
        return cls(**data)

