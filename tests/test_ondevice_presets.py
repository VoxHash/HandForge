"""Verify Android on-device encode presets against real FFmpeg."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

PRESETS = (
    Path(__file__).resolve().parents[1]
    / "companions"
    / "android"
    / "android"
    / "app"
    / "src"
    / "main"
    / "assets"
    / "encode_presets.json"
)

FFMPEG = shutil.which("ffmpeg")


@pytest.fixture(scope="module")
def presets_doc():
    assert PRESETS.is_file(), f"missing {PRESETS}"
    return json.loads(PRESETS.read_text(encoding="utf-8"))


def test_presets_schema(presets_doc):
    assert presets_doc.get("version") == 1
    presets = presets_doc["presets"]
    assert len(presets) >= 3
    ids = {p["id"] for p in presets}
    assert "audio_mp3_192" in ids
    assert "video_mp4_crf23" in ids
    for p in presets:
        assert p["extension"]
        assert isinstance(p["args"], list)
        assert all(isinstance(a, str) for a in p["args"])


@pytest.mark.skipif(not FFMPEG, reason="ffmpeg not on PATH")
def test_audio_presets_encode(tmp_path, presets_doc):
    src = tmp_path / "tone.wav"
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            str(src),
        ],
        check=True,
        capture_output=True,
    )
    for preset in presets_doc["presets"]:
        if not preset["id"].startswith("audio_"):
            continue
        out = tmp_path / f"{preset['id']}.{preset['extension']}"
        cmd = [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-i",
            str(src),
            *preset["args"],
            str(out),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr[-800:]
        assert out.is_file() and out.stat().st_size > 200


@pytest.mark.skipif(not FFMPEG, reason="ffmpeg not on PATH")
def test_video_preset_encode(tmp_path, presets_doc):
    src = tmp_path / "clip.mp4"
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=1:size=320x240:rate=15",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(src),
        ],
        check=True,
        capture_output=True,
    )
    preset = next(p for p in presets_doc["presets"] if p["id"] == "video_mp4_crf23")
    out = tmp_path / f"out.{preset['extension']}"
    cmd = [FFMPEG, "-y", "-hide_banner", "-i", str(src), *preset["args"], str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr[-800:]
    assert out.is_file() and out.stat().st_size > 500
