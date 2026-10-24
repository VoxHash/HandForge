"""Unit tests for FFmpeg helpers (command construction and path helpers)."""

from __future__ import annotations

import os

import pytest

from handforge.util.ffmpeg import (
    build_ffmpeg_cmd,
    find_external_cover,
    find_ffmpeg,
    find_ffprobe,
    is_audio_file,
    is_video_file,
    out_path,
)


def test_is_video_and_audio_extensions():
    assert is_video_file("/tmp/clip.mp4")
    assert is_video_file("movie.MKV")
    assert not is_video_file("song.mp3")
    assert is_audio_file("/tmp/song.flac")
    assert is_audio_file("track.M4A")
    assert not is_audio_file("clip.webm")


def test_find_ffmpeg_and_ffprobe_when_present():
    # On CI/dev machines with FFmpeg installed these return real paths.
    ffmpeg = find_ffmpeg()
    ffprobe = find_ffprobe()
    if shutil_which_ffmpeg():
        assert ffmpeg and os.path.isfile(ffmpeg)
        assert ffprobe and os.path.isfile(ffprobe)
    else:
        pytest.skip("FFmpeg not installed")


def shutil_which_ffmpeg() -> bool:
    import shutil

    return shutil.which("ffmpeg") is not None


def test_out_path_creates_dir_and_extension(tmp_path):
    dst_dir = tmp_path / "out"
    src = str(tmp_path / "My Song.flac")
    result = out_path(str(dst_dir), src, "mp3")
    assert dst_dir.is_dir()
    assert result == str(dst_dir / "My Song.mp3")
    assert out_path(str(dst_dir), src, "mkv").endswith(".mkv")


def test_find_external_cover(tmp_path):
    src = tmp_path / "track.mp3"
    src.write_bytes(b"x")
    assert find_external_cover(str(src)) is None
    cover = tmp_path / "cover.jpg"
    cover.write_bytes(b"jpg")
    assert find_external_cover(str(src)) == str(cover)


def test_build_audio_cbr_mp3_cmd(tmp_path):
    src = tmp_path / "a.wav"
    src.write_bytes(b"RIFF")
    dst = tmp_path / "a.mp3"
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp3",
        mode="CBR",
        bitrate="192",
        sample_rate="44100",
        channels="2",
    )
    assert cmd[0] == find_ffmpeg()
    assert "-i" in cmd and str(src) in cmd
    assert "-c:a" in cmd and "libmp3lame" in cmd
    assert "-b:a" in cmd and "192k" in cmd
    assert "-ar" in cmd and "44100" in cmd
    assert "-ac" in cmd and "2" in cmd
    assert cmd[-2:] == ["-y", str(dst)]
    assert "-vn" not in cmd  # audio-to-audio: no -vn needed


def test_video_to_video_maps_video_stream(tmp_path):
    src = tmp_path / "in.mkv"
    src.write_bytes(b"x")
    dst = tmp_path / "out.mp4"
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp4",
        bitrate="192",
    )
    assert "-vn" not in cmd
    assert "-map" in cmd and "0:v:0" in cmd
    assert "-c:v" in cmd and "libx264" in cmd
    assert "-c:a" in cmd


def test_video_to_audio_adds_vn(tmp_path):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    dst = tmp_path / "out.mp3"
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp3",
        mode="CBR",
        bitrate="128",
        extract_audio_only=True,
    )
    assert "-vn" in cmd
    assert "-c:a" in cmd and "libmp3lame" in cmd


def test_reduce_size_never_adds_vn(tmp_path):
    src = tmp_path / "big.mkv"
    src.write_bytes(b"x")
    dst = tmp_path / "small.mp4"
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp4",
        reduce_size=True,
        size_reduction_factor=7.0,
        extract_audio_only=True,  # must be overridden by reduce_size safety
    )
    assert "-vn" not in cmd
    assert "-crf" in cmd
    assert "-preset" in cmd and "slow" in cmd
    assert "0:v:0" in cmd


def test_reduce_size_hevc_codec(tmp_path):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    dst = tmp_path / "out.mp4"
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp4",
        reduce_size=True,
        use_hevc=True,
    )
    assert "libx265" in cmd


def test_metadata_and_strip(tmp_path):
    src = tmp_path / "a.wav"
    src.write_bytes(b"x")
    dst = tmp_path / "a.mp3"
    with_meta = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp3",
        bitrate="128",
        metadata={"title": "Hello", "artist": "Artist"},
        copy_meta=True,
    )
    assert "-map_metadata" in with_meta
    assert any(a.startswith("title=") for a in with_meta)
    stripped = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp3",
        bitrate="128",
        strip_meta=True,
        metadata={"title": "Nope"},
    )
    assert "-map_metadata" not in stripped
    assert not any(isinstance(a, str) and a.startswith("title=") for a in stripped)


def test_audio_trim_and_fade(tmp_path):
    src = tmp_path / "a.wav"
    src.write_bytes(b"x")
    dst = tmp_path / "a.mp3"
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp3",
        bitrate="128",
        trim_start=1.0,
        trim_end=3.5,
        fade_in=0.2,
        fade_out=0.3,
        normalize_lufs=True,
        target_lufs=-16.0,
    )
    assert "-ss" in cmd and "1.0" in cmd
    assert "-t" in cmd and "2.5" in cmd
    assert "-af" in cmd
    af = cmd[cmd.index("-af") + 1]
    assert "afade=t=in" in af
    assert "loudnorm=I=-16.0" in af


def test_video_trim_before_input(tmp_path):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    dst = tmp_path / "out.mp4"
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp4",
        video_trim_start=2.0,
        video_trim_end=5.0,
    )
    # -ss before -i for fast seek
    ss_idx = cmd.index("-ss")
    i_idx = cmd.index("-i")
    assert ss_idx < i_idx
    assert cmd[ss_idx + 1] == "2.0"
    assert "-t" in cmd and "3.0" in cmd
