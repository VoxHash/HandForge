"""Shared pytest fixtures for HandForge tests."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from handforge.util.ffmpeg import find_ffmpeg, find_ffprobe


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "ffmpeg: tests that require a working FFmpeg/ffprobe on PATH",
    )


@pytest.fixture(scope="session")
def ffmpeg_bin() -> str:
    path = find_ffmpeg()
    if not path:
        pytest.skip("FFmpeg not found on PATH")
    return path


@pytest.fixture(scope="session")
def ffprobe_bin() -> str:
    path = find_ffprobe()
    if not path:
        pytest.skip("ffprobe not found on PATH")
    return path


@pytest.fixture(scope="session")
def require_ffmpeg(ffmpeg_bin, ffprobe_bin):
    """Session gate: both ffmpeg and ffprobe must be available."""
    return ffmpeg_bin, ffprobe_bin


def _run_ffmpeg(ffmpeg: str, args: list[str], timeout: int = 60) -> None:
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", *args]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed ({result.returncode}): {' '.join(cmd)}\n{result.stderr}"
        )


class _MediaFactory:
    """Create short real media clips via lavfi (no mocks of the encode path)."""

    def __init__(self, tmp_path: Path, ffmpeg: str):
        self.tmp_path = tmp_path
        self._ffmpeg = ffmpeg

    def wav(self, name: str = "tone.wav", duration: float = 1.0) -> Path:
        out = self.tmp_path / name
        _run_ffmpeg(
            self._ffmpeg,
            [
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=440:duration={duration}",
                "-y",
                str(out),
            ],
        )
        assert out.is_file() and out.stat().st_size > 0
        return out

    def mp4(self, name: str = "clip.mp4", duration: float = 1.0) -> Path:
        out = self.tmp_path / name
        _run_ffmpeg(
            self._ffmpeg,
            [
                "-f",
                "lavfi",
                "-i",
                f"testsrc=duration={duration}:size=320x240:rate=10",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=440:duration={duration}",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                "-y",
                str(out),
            ],
            timeout=120,
        )
        assert out.is_file() and out.stat().st_size > 0
        return out


@pytest.fixture
def media_factory(tmp_path, require_ffmpeg):
    ffmpeg, _ffprobe = require_ffmpeg
    return _MediaFactory(tmp_path, ffmpeg)

@pytest.fixture
def isolated_config_dir(tmp_path, monkeypatch):
    """Redirect HandForge config I/O to a temp directory."""
    config_dir = tmp_path / "handforge_config"
    config_dir.mkdir()
    monkeypatch.setattr(
        "handforge.core.settings.get_config_dir",
        lambda: config_dir,
    )
    return config_dir


@pytest.fixture(scope="session")
def qapp():
    """QApplication for orchestrator / worker tests that need Qt."""
    pytest.importorskip("PyQt6")
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app
