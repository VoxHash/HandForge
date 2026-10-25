"""Unit and integration tests for advanced video filter graphs."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from handforge.util.ffmpeg import build_ffmpeg_cmd, find_ffmpeg, out_path, run_ffmpeg
from handforge.util.video_filters import (
    any_advanced_video_filter_enabled,
    build_video_filter_graph,
    join_video_filters,
    video_filter_kwargs_from_mapping,
)


def test_empty_graph_when_disabled():
    assert build_video_filter_graph() == []
    assert join_video_filters([]) is None


def test_color_eq_fragment():
    filters = build_video_filter_graph(
        video_color_enabled=True,
        video_brightness=0.1,
        video_contrast=1.2,
        video_saturation=0.8,
    )
    assert filters == ["eq=brightness=0.1:contrast=1.2:saturation=0.8"]


def test_color_enabled_identity_is_noop():
    assert (
        build_video_filter_graph(
            video_color_enabled=True,
            video_brightness=0.0,
            video_contrast=1.0,
            video_saturation=1.0,
        )
        == []
    )


def test_deshake_stabilize_fragment():
    filters = build_video_filter_graph(
        video_stabilize_enabled=True,
        video_stabilize_rx=32,
        video_stabilize_ry=16,
        video_stabilize_edge="clamp",
    )
    assert filters == ["deshake=rx=32:ry=16:edge=clamp"]


def test_deshake_rx_ry_snapped_to_multiple_of_16():
    filters = build_video_filter_graph(
        video_stabilize_enabled=True,
        video_stabilize_rx=24,  # → 16 or 32
        video_stabilize_ry=20,
    )
    assert filters == ["deshake=rx=32:ry=16:edge=mirror"]


def test_order_stabilize_then_color():
    filters = build_video_filter_graph(
        video_stabilize_enabled=True,
        video_color_enabled=True,
        video_brightness=0.05,
        video_contrast=1.1,
        video_saturation=1.0,
    )
    joined = join_video_filters(filters)
    assert joined is not None
    assert joined.startswith("deshake=")
    assert "eq=brightness=0.05:contrast=1.1:saturation=1" in joined
    assert joined.index("deshake=") < joined.index("eq=")


def test_invalid_edge_falls_back_to_mirror():
    filters = build_video_filter_graph(
        video_stabilize_enabled=True,
        video_stabilize_edge="nope",
    )
    assert filters == ["deshake=rx=16:ry=16:edge=mirror"]


def test_rx_ry_clamped():
    filters = build_video_filter_graph(
        video_stabilize_enabled=True,
        video_stabilize_rx=100,
        video_stabilize_ry=-5,
    )
    assert filters == ["deshake=rx=64:ry=0:edge=mirror"]


def test_rx_ry_eight_snaps_to_sixteen_or_zero():
    # 8 rounds to 16 (nearest multiple of 16)
    filters = build_video_filter_graph(
        video_stabilize_enabled=True,
        video_stabilize_rx=8,
        video_stabilize_ry=8,
    )
    assert filters == ["deshake=rx=16:ry=16:edge=mirror"]


def test_mapping_helper_and_any_enabled():
    kwargs = video_filter_kwargs_from_mapping(
        {"video_color_enabled": True, "video_brightness": 0.2}
    )
    assert kwargs["video_color_enabled"] is True
    assert kwargs["video_brightness"] == 0.2
    assert kwargs["video_stabilize_enabled"] is False
    assert any_advanced_video_filter_enabled(**kwargs) is True
    assert any_advanced_video_filter_enabled() is False


def test_build_ffmpeg_cmd_wires_vf_chain(tmp_path):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    dst = tmp_path / "out.mp4"
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp4",
        bitrate="128",
        video_color_enabled=True,
        video_brightness=0.1,
        video_contrast=1.15,
        video_saturation=0.9,
        video_stabilize_enabled=True,
        video_stabilize_rx=16,
        video_stabilize_ry=16,
        force_software=True,
        hw_accel="software",
    )
    assert "-vf" in cmd
    vf = cmd[cmd.index("-vf") + 1]
    assert vf.startswith("deshake=")
    assert "eq=brightness=0.1:contrast=1.15:saturation=0.9" in vf


def test_build_ffmpeg_cmd_no_advanced_vf_when_off(tmp_path):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    dst = tmp_path / "out.mp4"
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp4",
        bitrate="128",
        force_software=True,
        hw_accel="software",
    )
    # No crop/scale/hw → no -vf at all
    assert "-vf" not in cmd


def test_vf_order_with_crop_and_scale(tmp_path):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    dst = tmp_path / "out.mp4"
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp4",
        bitrate="128",
        crop_width=640,
        crop_height=360,
        crop_x=10,
        crop_y=20,
        resolution="1280x720",
        video_stabilize_enabled=True,
        video_color_enabled=True,
        video_brightness=0.05,
        video_contrast=1.0,
        video_saturation=1.1,
        force_software=True,
        hw_accel="software",
    )
    vf = cmd[cmd.index("-vf") + 1]
    parts = vf.split(",")
    assert parts[0].startswith("deshake=")
    assert parts[1] == "crop=640:360:10:20"
    assert parts[2].startswith("eq=")
    assert parts[3] == "scale=1280:720"


@pytest.mark.ffmpeg
def test_lavfi_pipeline_with_video_filters(tmp_path):
    """Integration: real FFmpeg encode with deshake + eq."""
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        pytest.skip("FFmpeg not available")

    filters_out = subprocess.run(
        [ffmpeg, "-hide_banner", "-filters"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    listing = (filters_out.stdout or "") + (filters_out.stderr or "")
    for name in ("eq", "deshake"):
        if name not in listing:
            pytest.skip(f"FFmpeg missing filter: {name}")

    src = tmp_path / "clip.mp4"
    gen = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x240:rate=15:duration=1.2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1.2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
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
    dst = Path(out_path(str(dst_dir), str(src), "mp4"))
    cmd = build_ffmpeg_cmd(
        src=str(src),
        dst=str(dst),
        fmt="mp4",
        mode="CBR",
        bitrate="128",
        video_color_enabled=True,
        video_brightness=0.05,
        video_contrast=1.1,
        video_saturation=0.95,
        video_stabilize_enabled=True,
        video_stabilize_rx=16,
        video_stabilize_ry=16,
        force_software=True,
        hw_accel="software",
    )
    assert "-vf" in cmd
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
