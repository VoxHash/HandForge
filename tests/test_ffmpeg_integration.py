"""Integration tests: real FFmpeg pipelines via lavfi-generated media."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from handforge.util.ffmpeg import (
    analyze_audio_quality,
    build_ffmpeg_cmd,
    get_audio_tracks,
    get_media_info,
    out_path,
    run_ffmpeg,
)


pytestmark = pytest.mark.ffmpeg


def _wait_proc(proc, timeout: float = 120) -> int:
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise


def _probe_streams(ffprobe: str, path: Path) -> dict:
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return json.loads(result.stdout)


def test_audio_wav_to_mp3_pipeline(media_factory, require_ffmpeg):
    _ffmpeg, ffprobe = require_ffmpeg
    src = media_factory.wav("tone.wav", duration=1.0)
    dst_dir = media_factory.tmp_path / "out_audio"
    dst = Path(out_path(str(dst_dir), str(src), "mp3"))

    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp3",
        mode="CBR",
        bitrate="128",
        metadata={"title": "HandForge Test", "artist": "CI"},
    )
    proc = run_ffmpeg(cmd)
    assert proc is not None
    assert _wait_proc(proc) == 0
    assert dst.is_file()
    assert dst.stat().st_size > 1024

    info = get_media_info(str(dst))
    assert info.get("duration", 0) > 0.5
    quality = analyze_audio_quality(str(dst))
    assert quality.get("codec") in ("mp3", "mp3float") or "mp3" in (
        quality.get("codec") or ""
    )

    data = _probe_streams(ffprobe, dst)
    assert any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    tags = data.get("format", {}).get("tags", {})
    # Tag keys vary by muxer casing
    tag_blob = {k.lower(): v for k, v in tags.items()}
    assert tag_blob.get("title") == "HandForge Test"
    assert tag_blob.get("artist") == "CI"


def test_video_to_video_preserves_video_stream(media_factory, require_ffmpeg):
    _ffmpeg, ffprobe = require_ffmpeg
    src = media_factory.mp4("clip.mp4", duration=1.0)
    dst_dir = media_factory.tmp_path / "out_v2v"
    dst = Path(out_path(str(dst_dir), str(src), "mp4"))

    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp4",
        video_quality="28",
        bitrate="128",
    )
    assert "-vn" not in cmd
    assert "0:v:0" in cmd

    proc = run_ffmpeg(cmd)
    assert proc is not None
    assert _wait_proc(proc) == 0
    assert dst.is_file()
    assert dst.stat().st_size >= 100 * 1024 or dst.stat().st_size > 10_000

    data = _probe_streams(ffprobe, dst)
    types = {s.get("codec_type") for s in data.get("streams", [])}
    assert "video" in types
    assert "audio" in types


def test_video_extract_audio_only(media_factory, require_ffmpeg):
    _ffmpeg, ffprobe = require_ffmpeg
    src = media_factory.mp4("clip_for_audio.mp4", duration=1.0)
    dst_dir = media_factory.tmp_path / "out_extract"
    dst = Path(out_path(str(dst_dir), str(src), "mp3"))

    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp3",
        mode="CBR",
        bitrate="96",
        extract_audio_only=True,
    )
    assert "-vn" in cmd

    proc = run_ffmpeg(cmd)
    assert proc is not None
    assert _wait_proc(proc) == 0
    assert dst.is_file() and dst.stat().st_size > 500

    data = _probe_streams(ffprobe, dst)
    types = {s.get("codec_type") for s in data.get("streams", [])}
    assert "audio" in types
    assert "video" not in types

    tracks = get_audio_tracks(str(src))
    assert len(tracks) >= 1
    assert tracks[0]["audio_index"] == 0


def test_audio_trim_pipeline(media_factory, require_ffmpeg):
    _ffmpeg, ffprobe = require_ffmpeg
    src = media_factory.wav("long_tone.wav", duration=3.0)
    dst_dir = media_factory.tmp_path / "out_trim"
    dst = Path(out_path(str(dst_dir), str(src), "wav"))

    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="wav",
        mode="Lossless",
        trim_start=0.5,
        trim_end=1.5,
    )
    proc = run_ffmpeg(cmd)
    assert proc is not None
    assert _wait_proc(proc) == 0

    info = get_media_info(str(dst))
    # Trimmed to ~1s (allow encoder/container slack)
    assert 0.7 <= info.get("duration", 0) <= 1.4


def test_worker_converts_real_wav(qapp, media_factory, require_ffmpeg):
    """End-to-end Worker thread with a real short WAV → MP3 conversion."""
    import time

    from PyQt6.QtCore import QCoreApplication

    from handforge.core.models import Job
    from handforge.core.orchestrator import Worker

    src = media_factory.wav("worker.wav", duration=0.8)
    out_dir = media_factory.tmp_path / "worker_out"
    out_dir.mkdir()

    job = Job(
        src=str(src),
        dst_dir=str(out_dir),
        format="mp3",
        mode="CBR",
        bitrate="128",
    )
    settings = {"on_exists": "overwrite", "ewma_alpha": 0.3}

    done = []
    progress_samples = []

    worker = Worker(1, job, settings)
    worker.sig_done.connect(lambda *a: done.append(a))
    worker.sig_progress.connect(lambda *a: progress_samples.append(a))
    worker.start()

    deadline = time.time() + 60
    while not done and time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.05)
    worker.wait(5000)

    assert done, "Worker did not finish"
    wid, success, message, output_path = done[0]
    assert success is True, message
    assert Path(output_path).is_file()
    assert Path(output_path).stat().st_size > 500
    # At least one progress emission (keepalive or real %)
    assert progress_samples
