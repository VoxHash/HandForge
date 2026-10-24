"""FFmpeg utilities for HandForge."""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List


def find_ffmpeg() -> Optional[str]:
    """Find FFmpeg executable."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    
    # Try common locations
    common_paths = [
        "C:\\ffmpeg\\bin\\ffmpeg.exe",
        "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",  # macOS (Apple Silicon)
        "/usr/local/opt/ffmpeg/bin/ffmpeg",  # macOS (Intel via Homebrew)
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None


def find_ffprobe() -> Optional[str]:
    """Find FFprobe executable."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        return ffprobe
    
    # Try common locations
    common_paths = [
        "C:\\ffmpeg\\bin\\ffprobe.exe",
        "C:\\Program Files\\ffmpeg\\bin\\ffprobe.exe",
        "/usr/bin/ffprobe",
        "/usr/local/bin/ffprobe",
        "/opt/homebrew/bin/ffprobe",  # macOS (Apple Silicon)
        "/usr/local/opt/ffmpeg/bin/ffprobe",  # macOS (Intel via Homebrew)
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None


def get_audio_tracks(src: str) -> List[Dict[str, Any]]:
    """Get list of audio tracks from video file."""
    ffprobe = find_ffprobe()
    if not ffprobe:
        return []
    
    try:
        import json
        cmd = [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "a",  # Only audio streams
            src
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return []
        
        data = json.loads(result.stdout)
        tracks = []
        audio_count = 0
        
        for stream in data.get("streams", []):
            index = stream.get("index", -1)
            codec = stream.get("codec_name", "unknown")
            lang = stream.get("tags", {}).get("language", "unknown")
            title = stream.get("tags", {}).get("title", "")
            channels = stream.get("channels", 0)
            sample_rate = stream.get("sample_rate", 0)
            
            tracks.append({
                "index": index,  # Actual stream index
                "audio_index": audio_count,  # Index among audio streams only (0-based)
                "codec": codec,
                "language": lang,
                "title": title or f"Audio {audio_count + 1} ({codec})",
                "channels": channels,
                "sample_rate": sample_rate,
            })
            audio_count += 1
        
        return tracks
    except Exception:
        return []


def get_subtitle_tracks(src: str) -> List[Dict[str, Any]]:
    """Get list of subtitle tracks from video file."""
    ffprobe = find_ffprobe()
    if not ffprobe:
        return []
    
    try:
        import json
        cmd = [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "s",  # Only subtitle streams
            src
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return []
        
        data = json.loads(result.stdout)
        tracks = []
        
        subtitle_count = 0
        for stream in data.get("streams", []):
            index = stream.get("index", -1)
            codec = stream.get("codec_name", "unknown")
            lang = stream.get("tags", {}).get("language", "unknown")
            title = stream.get("tags", {}).get("title", "")
            
            # subtitle_count is the index among subtitle streams (0, 1, 2, ...)
            # index is the actual stream index in the file
            tracks.append({
                "index": index,  # Actual stream index (for FFmpeg mapping)
                "subtitle_index": subtitle_count,  # Index among subtitle streams only (0-based)
                "codec": codec,
                "language": lang,
                "title": title or f"Subtitle {subtitle_count + 1} ({codec})"
            })
            subtitle_count += 1
        
        return tracks
    except Exception:
        return []


def is_video_file(path: str) -> bool:
    """Check if file is a video file."""
    ext = os.path.splitext(path)[1].lower()
    video_exts = [
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
        ".3gp", ".3g2", ".asf", ".rm", ".rmvb", ".vob", ".ogv", ".mts",
        ".m2ts", ".ts", ".divx", ".f4v", ".mxf", ".mpg", ".mpeg", ".m2v"
    ]
    return ext in video_exts


def is_audio_file(path: str) -> bool:
    """Check if file is an audio file."""
    ext = os.path.splitext(path)[1].lower()
    audio_exts = [
        ".mp3", ".aac", ".m4a", ".flac", ".wav", ".ogg", ".opus",
        ".wma", ".ac3", ".eac3", ".ape", ".tta", ".wv", ".mp2",
        ".amr", ".caf", ".au", ".mka", ".aiff"
    ]
    return ext in audio_exts


def build_ffmpeg_cmd(
    src: str,
    dst: str,
    fmt: str,
    mode: str = "CBR",
    bitrate: Optional[str] = None,
    vbrq: Optional[str] = None,
    sample_rate: Optional[str] = None,
    channels: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
    copy_meta: bool = True,
    strip_meta: bool = False,
    prefer_external_cover: bool = False,
    normalize_lufs: bool = False,
    target_lufs: float = -14.0,
    threads: int = 1,
    custom_args: Optional[str] = None,
    # Video options
    video_codec: Optional[str] = None,
    video_bitrate: Optional[str] = None,
    video_quality: Optional[str] = None,
    resolution: Optional[str] = None,
    fps: Optional[str] = None,
    extract_audio_only: bool = False,
    # Size reduction options
    reduce_size: bool = False,
    size_reduction_factor: Optional[float] = None,
    use_hevc: bool = False,
    two_pass: bool = False,
    # Subtitle options
    subtitle_track: Optional[int] = None,
    # Audio trimming and effects
    trim_start: Optional[float] = None,
    trim_end: Optional[float] = None,
    fade_in: Optional[float] = None,
    fade_out: Optional[float] = None,
    # Video trimming and cropping
    video_trim_start: Optional[float] = None,
    video_trim_end: Optional[float] = None,
    crop_x: Optional[int] = None,
    crop_y: Optional[int] = None,
    crop_width: Optional[int] = None,
    crop_height: Optional[int] = None,
    # Video quality preset
    video_quality_preset: Optional[str] = None,
    # Multiple audio tracks
    audio_track: Optional[int] = None,
    # Hardware acceleration preference: auto | software | nvenc | qsv | vaapi | videotoolbox
    hw_accel: Optional[str] = None,
    # Force software encoder (used after HW encode failure fallback)
    force_software: bool = False,
    # Advanced audio filters (EQ / compressor / limiter / denoise) — all off by default
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
    """Build FFmpeg command for audio or video conversion."""
    
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg not found. Please install FFmpeg and ensure it's on PATH.")

    def _append_audio_filters(cmd_list: List[str]) -> None:
        from .audio_filters import build_audio_filter_graph, join_audio_filters

        af = join_audio_filters(
            build_audio_filter_graph(
                fade_in=fade_in,
                fade_out=fade_out,
                normalize_lufs=normalize_lufs,
                target_lufs=target_lufs,
                eq_enabled=eq_enabled,
                eq_bass=eq_bass,
                eq_mid=eq_mid,
                eq_treble=eq_treble,
                compressor_enabled=compressor_enabled,
                compressor_threshold=compressor_threshold,
                compressor_ratio=compressor_ratio,
                compressor_attack=compressor_attack,
                compressor_release=compressor_release,
                compressor_makeup=compressor_makeup,
                limiter_enabled=limiter_enabled,
                limiter_limit=limiter_limit,
                limiter_attack=limiter_attack,
                limiter_release=limiter_release,
                denoise_enabled=denoise_enabled,
                denoise_nr=denoise_nr,
                denoise_nf=denoise_nf,
                denoise_track_noise=denoise_track_noise,
            )
        )
        if af:
            cmd_list.extend(["-af", af])
    
    # Determine if source is video
    src_is_video = is_video_file(src)
    # Determine if destination is video
    # For null device outputs (NUL, /dev/null), check source type instead
    if dst in ["NUL", "/dev/null"]:
        dst_is_video = src_is_video
    else:
        # Check destination path first, then fall back to format extension
        dst_is_video = is_video_file(dst)
        # If dst path doesn't exist yet, check format extension
        if not dst_is_video:
            # Check format directly from fmt parameter
            video_formats = ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", 
                           "3gp", "ogv", "mts", "m2ts", "ts"]
            dst_is_video = fmt.lower() in video_formats
    
    # Resolve HW encode plan early (pre-input args must precede -i).
    # When hw_accel is None, keep legacy software-only behavior for callers
    # that do not pass a preference; GUI/CLI always pass settings["hw_accel"].
    hw_plan = None
    if dst_is_video and (hw_accel is not None or force_software):
        from .hwaccel import resolve_hw_encode

        # Two-pass size reduction stays on software encoders (libx264/libx265).
        use_force_sw = force_software or (two_pass and reduce_size)
        soft_codec = video_codec
        if reduce_size and use_hevc and not video_codec:
            soft_codec = "libx265"
        elif not soft_codec:
            soft_codec = {
                "mp4": "libx264",
                "mkv": "libx264",
                "webm": "libvpx-vp9",
                "avi": "libx264",
                "mov": "libx264",
                "wmv": "wmv2",
                "flv": "libx264",
                "m4v": "libx264",
                "3gp": "libx264",
                "ogv": "libtheora",
            }.get(fmt.lower(), "libx264")
        hw_plan = resolve_hw_encode(
            hw_accel if hw_accel is not None else "software",
            software_codec=soft_codec,
            force_software=use_force_sw,
        )

    # Video trimming (must be before -i for faster seeking)
    cmd = [ffmpeg]
    if hw_plan and hw_plan.pre_input_args:
        cmd.extend(hw_plan.pre_input_args)
    if video_trim_start is not None:
        cmd.extend(["-ss", str(video_trim_start)])
    cmd.extend(["-i", src])
    
    # Video duration limit (after -i)
    if video_trim_end is not None and video_trim_start is not None:
        duration = video_trim_end - video_trim_start
        cmd.extend(["-t", str(duration)])
    elif video_trim_end is not None:
        cmd.extend(["-t", str(video_trim_end)])
    
    # Extract audio only from video
    # CRITICAL: Only add -vn if:
    # 1. Explicitly extracting audio only, AND
    # 2. Source is video but destination is NOT video (video-to-audio conversion)
    # NEVER add -vn if both source and destination are video (video-to-video conversion)
    # NEVER add -vn if reduce_size is True (we're compressing video, not extracting audio)
    should_extract_audio = False
    if extract_audio_only:
        # Explicitly requested audio extraction
        should_extract_audio = True
    elif src_is_video and not dst_is_video:
        # Video to audio conversion (destination format is audio)
        should_extract_audio = True
    
    # Safety check: Never extract audio if reduce_size is enabled (video compression)
    if reduce_size:
        should_extract_audio = False
    
    if should_extract_audio:
        # Video to audio extraction - no video stream
        cmd.extend(["-vn"])  # No video
        
        # Audio codec
        audio_codec_map = {
            "mp3": "libmp3lame",
            "aac": "aac",
            "m4a": "aac",
            "opus": "libopus",
            "ogg": "libvorbis",
            "flac": "flac",
            "wav": "pcm_s16le",
            "aiff": "pcm_s16be",
            "wma": "wmav2",
            "ac3": "ac3",
            "eac3": "eac3",
            "ape": "ape",
            "tta": "tta",
            "wv": "wavpack",
            "mp2": "mp2",
            "amr": "amr_nb",
            "caf": "pcm_s16be",
            "au": "pcm_s16be",
            "mka": "copy",
        }
        
        codec = audio_codec_map.get(fmt.lower(), "copy")
        cmd.extend(["-c:a", codec])
        
        # Audio encoding mode
        if mode == "CBR" and bitrate:
            cmd.extend(["-b:a", f"{bitrate}k"])
        elif mode == "VBR" and vbrq:
            if fmt.lower() == "mp3":
                cmd.extend(["-q:a", vbrq])
            elif fmt.lower() in ["aac", "m4a"]:
                cmd.extend(["-q:a", vbrq])
            elif fmt.lower() == "opus":
                cmd.extend(["-b:a", "0", "-vbr", "on", "-compression_level", vbrq])
            elif fmt.lower() == "ogg":
                cmd.extend(["-q:a", vbrq])
        elif mode == "Lossless":
            if fmt.lower() == "flac":
                cmd.extend(["-compression_level", "12"])
        
        # Sample rate
        if sample_rate:
            cmd.extend(["-ar", sample_rate])
        
        # Channels
        if channels:
            cmd.extend(["-ac", channels])
        
        # Audio trimming
        if trim_start is not None or trim_end is not None:
            start = trim_start if trim_start is not None else 0
            if trim_end is not None:
                duration = trim_end - start
                cmd.extend(["-ss", str(start), "-t", str(duration)])
            else:
                cmd.extend(["-ss", str(start)])
        
        _append_audio_filters(cmd)
    
    elif dst_is_video:
        # Video conversion
        from .hwaccel import apply_hw_rate_control, is_hw_encoder

        video_codec_map = {
            "mp4": "libx264",
            "mkv": "libx264",
            "webm": "libvpx-vp9",
            "avi": "libx264",
            "mov": "libx264",
            "wmv": "wmv2",
            "flv": "libx264",
            "m4v": "libx264",
            "3gp": "libx264",
            "ogv": "libtheora",
        }

        # Smart size reduction: Use H.265/HEVC for better compression
        if reduce_size and use_hevc:
            if fmt.lower() in ["mp4", "mkv", "m4v"]:
                soft_vcodec = "libx265"
            else:
                soft_vcodec = "libx264"
        elif video_codec:
            soft_vcodec = video_codec
        else:
            soft_vcodec = video_codec_map.get(fmt.lower(), "libx264")

        if hw_plan is not None:
            vcodec = hw_plan.encoder
        else:
            vcodec = soft_vcodec

        cmd.extend(["-c:v", vcodec])

        # Multiple audio track selection
        audio_map = "0:a:0"  # Default to first audio track
        if audio_track is not None and audio_track >= 0:
            audio_map = f"0:a:{audio_track}"

        # Subtitle handling - map streams explicitly to ensure video is included
        # CRITICAL: Always explicitly map video stream for video-to-video conversion
        if subtitle_track is not None and subtitle_track >= 0:
            cmd.extend(["-map", "0:v:0", "-map", audio_map, "-map", f"0:{subtitle_track}"])
            if fmt.lower() in ["mp4", "m4v"]:
                cmd.extend(["-c:s", "mov_text"])
            elif fmt.lower() == "mkv":
                cmd.extend(["-c:s", "copy"])
            else:
                cmd.extend(["-c:s", "mov_text"])
        else:
            cmd.extend(["-map", "0:v:0", "-map", audio_map])

        # Rate control / quality
        crf_for_reduce = None
        if reduce_size:
            if size_reduction_factor:
                if size_reduction_factor >= 8.0:
                    crf_for_reduce = "30"
                elif size_reduction_factor >= 5.0:
                    crf_for_reduce = "28"
                else:
                    crf_for_reduce = "26"
            else:
                crf_for_reduce = "28"

            if vcodec in ["libx264", "libx265"]:
                cmd.extend(["-preset", "slow"])
                if two_pass:
                    pass_logfile = dst + ".ffmpeg2pass"
                    cmd.extend(["-pass", "1"])
                    cmd.extend(["-passlogfile", pass_logfile])
                else:
                    cmd.extend(["-crf", crf_for_reduce])
            elif vcodec == "libvpx-vp9":
                cmd.extend(["-crf", crf_for_reduce, "-b:v", "0"])
            elif is_hw_encoder(vcodec):
                apply_hw_rate_control(
                    cmd,
                    encoder=vcodec,
                    video_bitrate=video_bitrate,
                    crf_value=crf_for_reduce,
                    preset="slow",
                )
        else:
            quality_preset_crf = None
            quality_preset_x264 = None
            if video_quality_preset:
                quality_map = {
                    "low": {"crf": "32", "preset": "fast"},
                    "medium": {"crf": "28", "preset": "medium"},
                    "high": {"crf": "23", "preset": "slow"},
                    "ultra": {"crf": "18", "preset": "veryslow"},
                }
                q = quality_map.get(video_quality_preset.lower())
                if q:
                    quality_preset_crf = q["crf"]
                    quality_preset_x264 = q["preset"]

            if is_hw_encoder(vcodec):
                apply_hw_rate_control(
                    cmd,
                    encoder=vcodec,
                    video_bitrate=video_bitrate,
                    video_quality=video_quality or quality_preset_crf,
                    preset=quality_preset_x264 or "medium",
                )
            else:
                if video_bitrate:
                    cmd.extend(["-b:v", f"{video_bitrate}k"])
                elif video_quality:
                    if vcodec in ["libx264", "libx265"]:
                        cmd.extend(["-crf", video_quality])
                    elif vcodec == "libvpx-vp9":
                        cmd.extend(["-crf", video_quality, "-b:v", "0"])
                elif quality_preset_crf:
                    if vcodec in ["libx264", "libx265"]:
                        cmd.extend(
                            ["-crf", quality_preset_crf, "-preset", quality_preset_x264]
                        )
                    elif vcodec == "libvpx-vp9":
                        cmd.extend(["-crf", quality_preset_crf, "-b:v", "0"])

                if (
                    vcodec in ["libx264", "libx265"]
                    and not reduce_size
                    and "-preset" not in cmd
                ):
                    cmd.extend(["-preset", quality_preset_x264 or "medium"])

        # Software filters first; HW upload filters last (VAAPI/QSV).
        sw_vf: List[str] = []
        if crop_width and crop_height:
            crop_filter = f"crop={crop_width}:{crop_height}"
            if crop_x is not None and crop_y is not None:
                crop_filter += f":{crop_x}:{crop_y}"
            sw_vf.append(crop_filter)
        if resolution:
            sw_vf.append(f"scale={resolution.replace('x', ':')}")
        hw_vf = list(hw_plan.vf_filters) if hw_plan and hw_plan.vf_filters else []
        vf_parts = sw_vf + hw_vf
        if vf_parts:
            cmd.extend(["-vf", ",".join(vf_parts)])

        # FPS - preserve original if not specified
        if fps:
            cmd.extend(["-r", fps])

        # Audio codec for video
        audio_codec_map = {
            "mp4": "aac",
            "mkv": "aac",
            "webm": "libopus",
            "avi": "aac",
            "mov": "aac",
            "wmv": "wmav2",
            "flv": "aac",
            "m4v": "aac",
            "3gp": "aac",
            "ogv": "libvorbis",
        }

        acodec = audio_codec_map.get(fmt.lower(), "aac")
        cmd.extend(["-c:a", acodec])

        # Audio bitrate for video
        if bitrate:
            cmd.extend(["-b:a", f"{bitrate}k"])
        elif not bitrate and acodec == "aac":
            cmd.extend(["-b:a", "192k"])  # Default audio bitrate

        # Sample rate
        if sample_rate:
            cmd.extend(["-ar", sample_rate])

        # Channels
        if channels:
            cmd.extend(["-ac", channels])

        _append_audio_filters(cmd)

    else:
        # Audio to audio conversion
        audio_codec_map = {
            "mp3": "libmp3lame",
            "aac": "aac",
            "m4a": "aac",
            "opus": "libopus",
            "ogg": "libvorbis",
            "flac": "flac",
            "wav": "pcm_s16le",
            "aiff": "pcm_s16be",
            "wma": "wmav2",
            "ac3": "ac3",
            "eac3": "eac3",
            "ape": "ape",
            "tta": "tta",
            "wv": "wavpack",
            "mp2": "mp2",
            "amr": "amr_nb",
            "caf": "pcm_s16be",
            "au": "pcm_s16be",
            "mka": "copy",
        }
        
        codec = audio_codec_map.get(fmt.lower(), "copy")
        cmd.extend(["-c:a", codec])
        
        # Encoding mode
        if mode == "CBR" and bitrate:
            if fmt.lower() in ["mp3", "aac", "m4a"]:
                cmd.extend(["-b:a", f"{bitrate}k"])
            elif fmt.lower() == "opus":
                cmd.extend(["-b:a", f"{bitrate}k"])
            elif fmt.lower() == "ogg":
                cmd.extend(["-b:a", f"{bitrate}k"])
        
        elif mode == "VBR" and vbrq:
            if fmt.lower() == "mp3":
                cmd.extend(["-q:a", vbrq])
            elif fmt.lower() in ["aac", "m4a"]:
                cmd.extend(["-q:a", vbrq])
            elif fmt.lower() == "opus":
                cmd.extend(["-b:a", "0", "-vbr", "on", "-compression_level", vbrq])
            elif fmt.lower() == "ogg":
                cmd.extend(["-q:a", vbrq])
        
        elif mode == "Lossless":
            if fmt.lower() == "flac":
                cmd.extend(["-compression_level", "12"])
        
        # Sample rate
        if sample_rate:
            cmd.extend(["-ar", sample_rate])
        
        # Channels
        if channels:
            cmd.extend(["-ac", channels])
        
        # Audio trimming
        if trim_start is not None or trim_end is not None:
            start = trim_start if trim_start is not None else 0
            if trim_end is not None:
                duration = trim_end - start
                cmd.extend(["-ss", str(start), "-t", str(duration)])
            else:
                cmd.extend(["-ss", str(start)])
        
        _append_audio_filters(cmd)
    
    # Metadata
    if not strip_meta:
        if copy_meta:
            cmd.append("-map_metadata")
            cmd.append("0")
        
        if metadata:
            for key, value in metadata.items():
                if value:
                    cmd.extend(["-metadata", f"{key}={value}"])
    
    # Cover art (for audio only)
    if not dst_is_video and prefer_external_cover:
        cover_path = find_external_cover(src)
        if cover_path and os.path.exists(cover_path):
            cmd.extend(["-i", cover_path, "-map", "0", "-map", "1", "-c:v", "copy", "-disposition:v", "attached_pic"])
    
    # Threads
    if threads > 1:
        cmd.extend(["-threads", str(threads)])
    
    # Custom arguments
    if custom_args:
        import shlex
        cmd.extend(shlex.split(custom_args))
    
    # Explicit format for null device outputs (NUL, /dev/null)
    if dst in ["NUL", "/dev/null"]:
        # Map format to FFmpeg format name
        format_map = {
            "mp4": "mp4",
            "mkv": "matroska",
            "webm": "webm",
            "avi": "avi",
            "mov": "mov",
            "wmv": "asf",
            "flv": "flv",
            "m4v": "mp4",
            "3gp": "3gp",
            "ogv": "ogg",
            "mp3": "mp3",
            "aac": "adts",
            "m4a": "mp4",
            "flac": "flac",
            "wav": "wav",
            "ogg": "ogg",
            "opus": "ogg",
        }
        ffmpeg_format = format_map.get(fmt.lower(), fmt.lower())
        cmd.extend(["-f", ffmpeg_format])
    
    # Output
    cmd.extend(["-y", dst])  # -y to overwrite
    
    return cmd


def find_external_cover(src: str) -> Optional[str]:
    """Find external cover art file."""
    src_dir = os.path.dirname(src)
    cover_names = ["cover.jpg", "folder.jpg", "cover.png", "folder.png", "cover.jpeg", "folder.jpeg"]
    
    for name in cover_names:
        cover_path = os.path.join(src_dir, name)
        if os.path.exists(cover_path):
            return cover_path
    
    return None


def run_ffmpeg(cmd: List[str]) -> Optional[subprocess.Popen]:
    """Run FFmpeg command."""
    try:
        # FFmpeg outputs progress to stderr
        # Use text mode and line buffering for better progress reading
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=False,  # Keep as bytes for better control
            bufsize=0,  # Unbuffered for real-time output
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return proc
    except Exception as e:
        print(f"Failed to start FFmpeg: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_media_info(src: str) -> Dict[str, Any]:
    """Get media file information (duration, bitrate, etc.) using ffprobe."""
    ffprobe = find_ffprobe()
    if not ffprobe:
        return {}
    
    try:
        import json
        cmd = [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            src
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return {}
        
        data = json.loads(result.stdout)
        info = {}
        
        # Get format info
        format_info = data.get("format", {})
        if "duration" in format_info:
            info["duration"] = float(format_info["duration"])
        if "bit_rate" in format_info:
            info["bitrate"] = int(format_info["bit_rate"]) // 1000  # Convert to kbps
        if "size" in format_info:
            info["size"] = int(format_info["size"])
        
        # Get stream info
        streams = data.get("streams", [])
        for stream in streams:
            codec_type = stream.get("codec_type", "")
            if codec_type == "audio":
                if "sample_rate" in stream:
                    info["sample_rate"] = int(stream["sample_rate"])
                if "channels" in stream:
                    info["channels"] = int(stream["channels"])
                break
        
        return info
    except Exception:
        return {}


def analyze_audio_quality(src: str) -> Dict[str, Any]:
    """Analyze audio quality metrics."""
    ffprobe = find_ffprobe()
    if not ffprobe:
        return {}
    
    try:
        import json
        cmd = [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "a:0",  # First audio stream
            src
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return {}
        
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        if not streams:
            return {}
        
        stream = streams[0]
        quality_info = {
            "codec": stream.get("codec_name", "unknown"),
            "bitrate": int(stream.get("bit_rate", 0)) // 1000 if stream.get("bit_rate") else None,
            "sample_rate": int(stream.get("sample_rate", 0)) if stream.get("sample_rate") else None,
            "channels": int(stream.get("channels", 0)) if stream.get("channels") else None,
            "codec_long_name": stream.get("codec_long_name", ""),
        }
        
        return quality_info
    except Exception:
        return {}


def out_path(dst_dir: str, src: str, fmt: str) -> str:
    """Generate output path for converted file."""
    # Expand user directory
    dst_dir = os.path.expanduser(dst_dir)
    
    # Create directory if it doesn't exist with proper permissions
    try:
        os.makedirs(dst_dir, mode=0o755, exist_ok=True)
    except PermissionError:
        # If permission denied, try with default mode
        try:
            os.makedirs(dst_dir, exist_ok=True)
        except PermissionError as e:
            raise PermissionError(f"Cannot create output directory '{dst_dir}': {e}. Please check permissions or choose a different output directory.")
    
    # Verify directory is writable
    if not os.access(dst_dir, os.W_OK):
        # Try to fix permissions if possible
        try:
            import stat
            current_mode = os.stat(dst_dir).st_mode
            # Add write permission for owner
            os.chmod(dst_dir, current_mode | stat.S_IWUSR)
            if not os.access(dst_dir, os.W_OK):
                raise PermissionError(f"Output directory '{dst_dir}' is not writable. Please check permissions or choose a different output directory.")
        except (PermissionError, OSError) as e:
            raise PermissionError(f"Output directory '{dst_dir}' is not writable: {e}. Please check permissions or choose a different output directory.")
    
    # Get source filename without extension
    src_basename = os.path.basename(src)
    src_name, _ = os.path.splitext(src_basename)
    
    # Output extension map (audio + video)
    ext_map = {
        # Audio
        "mp3": ".mp3",
        "aac": ".aac",
        "m4a": ".m4a",
        "opus": ".opus",
        "ogg": ".ogg",
        "flac": ".flac",
        "wav": ".wav",
        "aiff": ".aiff",
        "wma": ".wma",
        "ac3": ".ac3",
        "eac3": ".eac3",
        "ape": ".ape",
        "tta": ".tta",
        "wv": ".wv",
        "mp2": ".mp2",
        "amr": ".amr",
        "caf": ".caf",
        "au": ".au",
        "mka": ".mka",
        # Video
        "mp4": ".mp4",
        "mkv": ".mkv",
        "avi": ".avi",
        "mov": ".mov",
        "wmv": ".wmv",
        "flv": ".flv",
        "webm": ".webm",
        "m4v": ".m4v",
        "3gp": ".3gp",
        "ogv": ".ogv",
    }
    
    ext = ext_map.get(fmt.lower(), f".{fmt}")
    output_file = os.path.join(dst_dir, f"{src_name}{ext}")
    
    # Check if output file exists and has wrong permissions
    if os.path.exists(output_file):
        try:
            # Try to make file writable if it exists
            import stat
            current_mode = os.stat(output_file).st_mode
            os.chmod(output_file, current_mode | stat.S_IWUSR)
        except (PermissionError, OSError):
            # If we can't fix permissions, that's okay - FFmpeg will handle overwrite
            pass
    
    return output_file
