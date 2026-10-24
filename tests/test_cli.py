"""Unit and smoke tests for the headless HandForge CLI."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from handforge.cli import (
    EXIT_OK,
    EXIT_USAGE,
    build_job,
    build_parser,
    cmd_convert,
    collect_inputs,
    main,
    resolve_conversion_options,
)
from handforge.core.presets import BUILTIN_PRESETS, get_preset
from handforge.util.ffmpeg import out_path


def test_parser_help_exits_zero():
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--help"])
    assert exc.value.code == 0


def test_main_list_presets(capsys, isolated_config_dir):
    code = main(["list-presets"])
    assert code == EXIT_OK
    out = capsys.readouterr().out
    assert "MP3 192k" in out
    assert "AAC 256k" in out
    assert "format=mp3" in out


def test_collect_inputs_files_and_dirs(tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF")
    nested = tmp_path / "sub"
    nested.mkdir()
    video = nested / "clip.mp4"
    video.write_bytes(b"ftyp")
    junk = nested / "readme.txt"
    junk.write_text("nope")

    found = collect_inputs([str(audio), str(tmp_path)])
    assert str(audio.resolve()) in found
    assert str(video.resolve()) in found
    assert len(found) == 2


def test_collect_inputs_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        collect_inputs([str(tmp_path / "missing.mp3")])


def test_resolve_preset_and_overrides():
    args = SimpleNamespace(
        preset="MP3 192k",
        format="flac",
        mode="Lossless",
        bitrate=None,
        vbrq=None,
        video_codec=None,
        video_quality=None,
        video_bitrate=None,
        extract_audio=False,
    )
    opts = resolve_conversion_options(args)
    assert opts["format"] == "flac"
    assert opts["mode"] == "Lossless"


def test_resolve_unknown_preset():
    args = SimpleNamespace(
        preset="Does Not Exist",
        format=None,
        mode=None,
        bitrate=None,
        vbrq=None,
        video_codec=None,
        video_quality=None,
        video_bitrate=None,
        extract_audio=False,
    )
    with pytest.raises(ValueError, match="Unknown preset"):
        resolve_conversion_options(args)


def test_get_builtin_preset():
    preset = get_preset("MP3 192k")
    assert preset == BUILTIN_PRESETS["MP3 192k"]


def test_build_job_applies_audio_preset(tmp_path):
    src = str(tmp_path / "song.wav")
    Path(src).write_bytes(b"x")
    opts = get_preset("AAC 256k")
    job = build_job(src, str(tmp_path / "out"), opts, {})
    assert job.format == "aac"
    assert job.bitrate == "256"
    assert job.mode == "CBR"


def test_cmd_convert_no_media_returns_usage(tmp_path, isolated_config_dir):
    empty = tmp_path / "empty"
    empty.mkdir()
    args = build_parser().parse_args(
        ["convert", str(empty), "-o", str(tmp_path / "out"), "--format", "mp3"]
    )
    assert cmd_convert(args) == EXIT_USAGE


def test_cmd_convert_missing_input_returns_usage(tmp_path, isolated_config_dir):
    args = build_parser().parse_args(
        [
            "convert",
            str(tmp_path / "nope.wav"),
            "-o",
            str(tmp_path / "out"),
            "--format",
            "mp3",
        ]
    )
    assert cmd_convert(args) == EXIT_USAGE


@pytest.mark.ffmpeg
def test_cli_real_wav_to_mp3(media_factory, require_ffmpeg, qapp, isolated_config_dir, capsys):
    """Smoke: real lavfi WAV → MP3 through CLI → Orchestrator → FFmpeg."""
    src = media_factory.wav("cli_tone.wav", duration=0.5)
    out_dir = media_factory.tmp_path / "cli_out"
    code = main(
        [
            "convert",
            str(src),
            "--preset",
            "MP3 192k",
            "-o",
            str(out_dir),
            "--parallel",
            "1",
            "--no-adaptive",
            "--quiet",
        ]
    )
    assert code == EXIT_OK
    dst = Path(out_path(str(out_dir), str(src), "mp3"))
    assert dst.is_file()
    assert dst.stat().st_size > 500
    captured = capsys.readouterr()
    assert str(dst) in captured.out


@pytest.mark.ffmpeg
def test_cli_subprocess_help_and_convert(
    media_factory, require_ffmpeg, isolated_config_dir, tmp_path
):
    """End-to-end process: help + short conversion without a display."""
    import subprocess
    import sys

    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["HOME"] = str(tmp_path / "home")
    (tmp_path / "home").mkdir()

    help_proc = subprocess.run(
        [sys.executable, "-m", "handforge", "--help"],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert help_proc.returncode == 0
    assert "convert" in help_proc.stdout
    assert "list-presets" in help_proc.stdout

    src = media_factory.wav("subproc_tone.wav", duration=0.4)
    out_dir = media_factory.tmp_path / "subproc_out"
    conv = subprocess.run(
        [
            sys.executable,
            "-m",
            "handforge",
            "convert",
            str(src),
            "-f",
            "mp3",
            "--bitrate",
            "128",
            "-o",
            str(out_dir),
            "--parallel",
            "1",
            "--no-adaptive",
            "-q",
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert conv.returncode == 0, conv.stderr
    dst = Path(out_path(str(out_dir), str(src), "mp3"))
    assert dst.is_file() and dst.stat().st_size > 400
