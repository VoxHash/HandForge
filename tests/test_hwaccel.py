"""Unit tests for hardware encoder detection, selection, and fallback."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from handforge.util import hwaccel as hw
from handforge.util.ffmpeg import build_ffmpeg_cmd, find_ffmpeg


@pytest.fixture(autouse=True)
def _clear_hw_cache():
    hw.clear_detection_cache()
    yield
    hw.clear_detection_cache()


def test_normalize_hw_preference_aliases():
    assert hw.normalize_hw_preference(None) == "auto"
    assert hw.normalize_hw_preference("NVENC") == "nvenc"
    assert hw.normalize_hw_preference("QuickSync") == "qsv"
    assert hw.normalize_hw_preference("cpu") == "software"
    assert hw.normalize_hw_preference("nope") == "auto"


def test_codec_family_and_software_fallback():
    assert hw.codec_family("libx264") == "h264"
    assert hw.codec_family("hevc_nvenc") == "hevc"
    assert hw.codec_family("libvpx-vp9") is None
    assert hw.software_fallback_codec("h264_vaapi") == "libx264"
    assert hw.software_fallback_codec("hevc_qsv") == "libx265"
    assert hw.is_hw_encoder("h264_nvenc")
    assert not hw.is_hw_encoder("libx264")


def test_resolve_software_preference_never_uses_hw():
    detection = {
        "backends": {"nvenc": True, "qsv": True, "vaapi": True, "videotoolbox": False},
        "encoders": {
            "nvenc": {"h264": "h264_nvenc", "hevc": "hevc_nvenc"},
            "qsv": {"h264": "h264_qsv"},
            "vaapi": {"h264": "h264_vaapi"},
        },
        "vaapi_device": "/dev/dri/renderD128",
    }
    plan = hw.resolve_hw_encode(
        "software", software_codec="libx264", detection=detection
    )
    assert plan.backend == "software"
    assert plan.encoder == "libx264"
    assert plan.used_hw is False


def test_resolve_auto_picks_first_available():
    detection = {
        "backends": {"nvenc": False, "qsv": False, "vaapi": True, "videotoolbox": False},
        "encoders": {"vaapi": {"h264": "h264_vaapi", "hevc": "hevc_vaapi"}},
        "vaapi_device": "/dev/dri/renderD129",
    }
    plan = hw.resolve_hw_encode("auto", software_codec="libx264", detection=detection)
    assert plan.backend == "vaapi"
    assert plan.encoder == "h264_vaapi"
    assert plan.used_hw is True
    assert plan.pre_input_args[:2] == ["-init_hw_device", "vaapi=va:/dev/dri/renderD129"]
    assert "hwupload" in ",".join(plan.vf_filters)


def test_resolve_auto_falls_back_when_none_available():
    detection = {
        "backends": {
            "nvenc": False,
            "qsv": False,
            "vaapi": False,
            "videotoolbox": False,
        },
        "encoders": {},
        "vaapi_device": None,
    }
    plan = hw.resolve_hw_encode("auto", software_codec="libx265", detection=detection)
    assert plan.backend == "software"
    assert plan.encoder == "libx265"
    assert plan.used_hw is False


def test_resolve_explicit_backend_unavailable_falls_back():
    detection = {
        "backends": {"nvenc": False, "qsv": False, "vaapi": False, "videotoolbox": False},
        "encoders": {},
    }
    plan = hw.resolve_hw_encode("nvenc", software_codec="libx264", detection=detection)
    assert plan.encoder == "libx264"
    assert plan.used_hw is False


def test_resolve_hevc_family_maps_nvenc():
    detection = {
        "backends": {"nvenc": True, "qsv": False, "vaapi": False, "videotoolbox": False},
        "encoders": {"nvenc": {"h264": "h264_nvenc", "hevc": "hevc_nvenc"}},
    }
    plan = hw.resolve_hw_encode("auto", software_codec="libx265", detection=detection)
    assert plan.encoder == "hevc_nvenc"
    assert plan.family == "hevc"


def test_vp9_not_mapped_to_hw():
    detection = {
        "backends": {"nvenc": True, "qsv": False, "vaapi": False, "videotoolbox": False},
        "encoders": {"nvenc": {"h264": "h264_nvenc"}},
    }
    plan = hw.resolve_hw_encode("auto", software_codec="libvpx-vp9", detection=detection)
    assert plan.encoder == "libvpx-vp9"
    assert plan.used_hw is False


def test_force_software_overrides_preference():
    detection = {
        "backends": {"nvenc": True, "qsv": False, "vaapi": False, "videotoolbox": False},
        "encoders": {"nvenc": {"h264": "h264_nvenc"}},
    }
    plan = hw.resolve_hw_encode(
        "nvenc", software_codec="libx264", detection=detection, force_software=True
    )
    assert plan.encoder == "libx264"
    assert plan.used_hw is False


def test_build_cmd_with_software_pref_keeps_libx264(tmp_path):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    dst = tmp_path / "out.mp4"
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp4",
        bitrate="192",
        hw_accel="software",
    )
    assert "-c:v" in cmd and "libx264" in cmd
    assert "h264_nvenc" not in cmd
    assert "h264_vaapi" not in cmd


def test_build_cmd_with_vaapi_pref_injects_device(tmp_path):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    dst = tmp_path / "out.mp4"
    detection = {
        "backends": {"nvenc": False, "qsv": False, "vaapi": True, "videotoolbox": False},
        "encoders": {"vaapi": {"h264": "h264_vaapi"}},
        "vaapi_device": "/dev/dri/renderD129",
    }
    with patch(
        "handforge.util.hwaccel.detect_available_backends", return_value=detection
    ):
        cmd = build_ffmpeg_cmd(
            src=str(src),
            dst=str(dst),
            fmt="mp4",
            bitrate="192",
            hw_accel="vaapi",
        )
    assert "h264_vaapi" in cmd
    assert "-init_hw_device" in cmd
    assert any(a.startswith("vaapi=va:") for a in cmd)
    assert "-vf" in cmd
    vf = cmd[cmd.index("-vf") + 1]
    assert "hwupload" in vf
    # init must come before -i
    assert cmd.index("-init_hw_device") < cmd.index("-i")


def test_build_cmd_none_hw_accel_unchanged_software(tmp_path):
    """Legacy callers that omit hw_accel keep software-only commands."""
    src = tmp_path / "in.mkv"
    src.write_bytes(b"x")
    dst = tmp_path / "out.mp4"
    cmd = build_ffmpeg_cmd(src=str(src), dst=str(dst), fmt="mp4", bitrate="192")
    assert "libx264" in cmd


def test_looks_like_hw_failure():
    assert hw.looks_like_hw_failure("OpenEncodeSession failed")
    assert hw.looks_like_hw_failure("Failed to initialise VAAPI connection")
    assert hw.looks_like_hw_failure("")  # empty → treat as HW-ish for retry


def test_list_compiled_encoders_when_ffmpeg_present():
    if not find_ffmpeg():
        pytest.skip("FFmpeg not installed")
    names = hw.list_compiled_encoders()
    assert "libx264" in names or "libx265" in names


def test_detect_available_backends_probes_host():
    if not find_ffmpeg():
        pytest.skip("FFmpeg not installed")
    info = hw.detect_available_backends(probe=True, force_refresh=True)
    assert info.get("ffmpeg")
    assert "backends" in info
    assert set(info["backends"]) >= {"nvenc", "qsv", "vaapi", "videotoolbox"}
    # Report should be printable
    report = hw.format_detection_report(info)
    assert "FFmpeg:" in report


def test_hw_encode_integration_when_available(tmp_path):
    """Run a real HW encode only when a backend probes successfully."""
    if not find_ffmpeg():
        pytest.skip("FFmpeg not installed")
    info = hw.detect_available_backends(probe=True, force_refresh=True)
    backends = info.get("backends") or {}
    available = [b for b, ok in backends.items() if ok]
    if not available:
        pytest.skip("No working hardware encoders on this host")

    # Generate a tiny source clip with software encode first.
    src = tmp_path / "src.mp4"
    import subprocess

    gen = subprocess.run(
        [
            find_ffmpeg(),
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x240:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.5",
            "-t",
            "0.5",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(src),
        ],
        capture_output=True,
        text=True,
    )
    if gen.returncode != 0:
        pytest.skip(f"Could not generate test clip: {gen.stderr[-200:]}")

    backend = available[0]
    dst = tmp_path / f"out_{backend}.mp4"
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp4",
        bitrate="128",
        video_quality="28",
        hw_accel=backend,
    )
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr[-500:]
    assert dst.is_file() and dst.stat().st_size > 500
    vcodec = cmd[cmd.index("-c:v") + 1]
    assert hw.is_hw_encoder(vcodec)
