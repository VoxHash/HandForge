"""Sanity checks for the multi-ABI Android FFmpeg fetch script (no large downloads in CI)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "fetch-android-ffmpeg.sh"
JNILIBS = ROOT / "companions" / "android" / "android" / "app" / "src" / "main" / "jniLibs"


def test_fetch_script_exists_and_is_executable():
    assert SCRIPT.is_file()
    assert os.access(SCRIPT, os.X_OK), f"{SCRIPT} must be executable"


def test_fetch_script_help():
    proc = subprocess.run(
        [str(SCRIPT), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    out = proc.stdout + proc.stderr
    assert "fetch-android-ffmpeg" in out or "jniLibs" in out
    assert "armeabi-v7a" in out or "arm64-v8a" in out


def test_jniLibs_placeholders_present():
    assert (JNILIBS / "README.md").is_file()
    assert (JNILIBS / "armeabi-v7a" / ".gitkeep").is_file()
    assert (JNILIBS / "arm64-v8a" / ".gitkeep").is_file()


def test_check_mode_without_blobs_fails_clearly():
    """When libs are absent (default git checkout), --check must fail without downloading."""
    arm64 = JNILIBS / "arm64-v8a" / "libffmpeg.so"
    if arm64.is_file():
        pytest.skip("bundled libs already present on this machine")
    proc = subprocess.run(
        [str(SCRIPT), "--check"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "MISSING" in (proc.stdout + proc.stderr) or "incomplete" in (
        proc.stdout + proc.stderr
    ).lower()
