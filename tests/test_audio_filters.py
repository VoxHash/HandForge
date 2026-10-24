"""Unit and integration tests for advanced audio filter graphs."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from handforge.util.audio_filters import (
    any_advanced_audio_filter_enabled,
    audio_filter_kwargs_from_mapping,
    build_audio_filter_graph,
    join_audio_filters,
)
from handforge.util.ffmpeg import build_ffmpeg_cmd, find_ffmpeg, out_path, run_ffmpeg


def test_empty_graph_when_disabled():
    assert build_audio_filter_graph() == []
    assert join_audio_filters([]) is None


def test_eq_bands_only_nonzero_gains():
    filters = build_audio_filter_graph(
        eq_enabled=True,
        eq_bass=3.0,
        eq_mid=0.0,
        eq_treble=-2.5,
    )
    assert len(filters) == 2
    assert filters[0].startswith("equalizer=f=100:")
    assert "g=3" in filters[0]
    assert filters[1].startswith("equalizer=f=8000:")
    assert "g=-2.5" in filters[1]


def test_eq_enabled_all_zero_is_noop():
    assert build_audio_filter_graph(eq_enabled=True) == []


def test_compressor_limiter_denoise_fragments():
    filters = build_audio_filter_graph(
        denoise_enabled=True,
        denoise_nr=10,
        denoise_nf=-40,
        denoise_track_noise=True,
        compressor_enabled=True,
        compressor_threshold=0.1,
        compressor_ratio=3,
        compressor_attack=15,
        compressor_release=200,
        compressor_makeup=1.5,
        limiter_enabled=True,
        limiter_limit=0.9,
        limiter_attack=5,
        limiter_release=50,
    )
    joined = join_audio_filters(filters)
    assert joined is not None
    assert joined.startswith("afftdn=nr=10:nf=-40:tn=1")
    assert "acompressor=threshold=0.1:ratio=3:attack=15:release=200:makeup=1.5" in joined
    assert "alimiter=limit=0.9:attack=5:release=50:level=disabled" in joined
    # Order: denoise → compressor → limiter
    assert joined.index("afftdn=") < joined.index("acompressor=")
    assert joined.index("acompressor=") < joined.index("alimiter=")


def test_legacy_fade_and_loudnorm_still_appended():
    filters = build_audio_filter_graph(
        fade_in=0.2,
        fade_out=0.3,
        normalize_lufs=True,
        target_lufs=-16.0,
        eq_enabled=True,
        eq_mid=1.0,
    )
    joined = join_audio_filters(filters)
    assert joined is not None
    assert "equalizer=f=1000:" in joined
    assert "afade=t=in" in joined
    assert "loudnorm=I=-16.0" in joined
    assert joined.index("equalizer=") < joined.index("afade=")
    assert joined.index("afade=") < joined.index("loudnorm=")


def test_mapping_helper_and_any_enabled():
    kwargs = audio_filter_kwargs_from_mapping({"eq_enabled": True, "eq_bass": 2})
    assert kwargs["eq_enabled"] is True
    assert kwargs["eq_bass"] == 2
    assert kwargs["compressor_enabled"] is False
    assert any_advanced_audio_filter_enabled(**kwargs) is True
    assert any_advanced_audio_filter_enabled() is False


def test_build_ffmpeg_cmd_wires_af_chain(tmp_path):
    src = tmp_path / "a.wav"
    src.write_bytes(b"x")
    dst = tmp_path / "a.mp3"
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp3",
        bitrate="128",
        eq_enabled=True,
        eq_bass=2.0,
        compressor_enabled=True,
        limiter_enabled=True,
        denoise_enabled=True,
        denoise_nr=8,
        denoise_nf=-45,
    )
    assert "-af" in cmd
    af = cmd[cmd.index("-af") + 1]
    assert "afftdn=" in af
    assert "equalizer=" in af
    assert "acompressor=" in af
    assert "alimiter=" in af


def test_build_ffmpeg_cmd_no_af_when_filters_off(tmp_path):
    src = tmp_path / "a.wav"
    src.write_bytes(b"x")
    dst = tmp_path / "a.mp3"
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp3",
        bitrate="128",
    )
    assert "-af" not in cmd


def test_video_path_gets_audio_filters(tmp_path):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    dst = tmp_path / "out.mp4"
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp4",
        bitrate="128",
        denoise_enabled=True,
        denoise_nr=12,
        denoise_nf=-50,
        denoise_track_noise=False,
    )
    assert "-af" in cmd
    af = cmd[cmd.index("-af") + 1]
    assert af == "afftdn=nr=12:nf=-50"


@pytest.mark.ffmpeg
def test_lavfi_pipeline_with_full_audio_filter_chain(tmp_path):
    """Integration: real FFmpeg encode with EQ + compressor + limiter + denoise."""
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        pytest.skip("FFmpeg not available")

    # Verify filters are compiled into this FFmpeg build
    filters_out = subprocess.run(
        [ffmpeg, "-hide_banner", "-filters"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    listing = (filters_out.stdout or "") + (filters_out.stderr or "")
    for name in ("equalizer", "acompressor", "alimiter", "afftdn"):
        if name not in listing:
            pytest.skip(f"FFmpeg missing filter: {name}")

    src = tmp_path / "tone.wav"
    gen = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1.5",
            "-c:a",
            "pcm_s16le",
            str(src),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert gen.returncode == 0, gen.stderr
    assert src.is_file()

    dst_dir = tmp_path / "out"
    dst = Path(out_path(str(dst_dir), str(src), "mp3"))
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp3",
        mode="CBR",
        bitrate="128",
        eq_enabled=True,
        eq_bass=2.0,
        eq_treble=-1.0,
        compressor_enabled=True,
        compressor_threshold=0.125,
        compressor_ratio=4.0,
        limiter_enabled=True,
        limiter_limit=0.95,
        denoise_enabled=True,
        denoise_nr=10.0,
        denoise_nf=-50.0,
        denoise_track_noise=True,
    )
    assert "-af" in cmd
    proc = run_ffmpeg(cmd)
    assert proc is not None
    try:
        code = proc.wait(timeout=120)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise
    assert code == 0
    assert dst.is_file()
    assert dst.stat().st_size > 512
