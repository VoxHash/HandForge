"""Unit tests for actionable error mapping."""

from __future__ import annotations

import errno

import pytest

from handforge.util.errors import (
    ActionableError,
    classify_error,
    extract_ffmpeg_error_hint,
    format_actionable_error,
)


@pytest.mark.parametrize(
    "raw,expected_code",
    [
        ("FFmpeg not found. Please install FFmpeg and ensure it's on PATH.", "ffmpeg_missing"),
        ("Failed to start FFmpeg - check if FFmpeg is installed and on PATH", "ffmpeg_missing"),
        ("No space left on device", "disk_full"),
        ("OSError: [Errno 28] No space left on device: '/out/a.mp3'", "disk_full"),
        ("Permission denied: '/root/out'", "permission_denied"),
        ("Output directory is not writable: /opt/secure", "permission_denied"),
        ("Cannot write to output directory '/tmp/x': Permission denied", "permission_denied"),
        ("Source file not found: /missing/track.flac", "source_missing"),
        ("Input not found: /gone.wav", "source_missing"),
        ("Unknown encoder 'libx265'", "unsupported_encoder"),
        ("Error initializing output stream 0:0 -- Error while opening encoder", "unsupported_encoder"),
        ("Unknown decoder 'exotic'", "unsupported_decoder"),
        ("Could not write header for output file", "unsupported_muxer"),
        ("Invalid data found when processing input", "corrupt_input"),
        ("moov atom not found", "corrupt_input"),
        ("Error reinitializing filters!", "filter_graph"),
        ("Conversion completed but output file has no video stream - video was not included", "missing_video"),
        ("Output file is too small (12 bytes) - conversion may have failed", "output_incomplete"),
        ("Conversion timed out after 1 hour", "timeout"),
        ("Stopped by user", "stopped"),
    ],
)
def test_classify_common_failure_modes(raw: str, expected_code: str):
    err = classify_error(raw)
    assert err.code == expected_code
    assert err.title
    assert err.summary
    assert err.solutions
    text = err.format()
    assert "What to try:" in text
    assert "1." in text


def test_classify_from_stderr_when_message_generic():
    stderr = "\n".join(
        [
            "frame=  10 fps=0.0 q=0.0 size=       0kB",
            "[libx265 @ 0x1] Unknown encoder 'libx265'",
            "Error initializing output stream 0:0",
        ]
    )
    err = classify_error("Conversion failed with exit code 1", stderr=stderr)
    assert err.code == "unsupported_encoder"
    assert "encoder" in err.summary.lower() or "codec" in err.summary.lower()


def test_classify_oserror_enospc():
    exc = OSError(errno.ENOSPC, "No space left on device")
    err = classify_error("write failed", exc=exc)
    assert err.code == "disk_full"


def test_classify_oserror_eacces():
    exc = OSError(errno.EACCES, "Permission denied")
    err = classify_error("cannot open", exc=exc)
    assert err.code == "permission_denied"


def test_format_actionable_error_includes_steps():
    text = format_actionable_error("FFmpeg not found on PATH")
    assert "FFmpeg" in text
    assert "What to try:" in text
    assert "ffmpeg -version" in text


def test_format_without_solutions():
    text = format_actionable_error(
        "Permission denied writing to /x",
        include_solutions=False,
    )
    assert "What to try:" not in text
    assert "permission" in text.lower() or "Permission" in text or "writable" in text.lower() or "write" in text.lower()


def test_short_truncates():
    err = ActionableError(
        code="unknown",
        title="X",
        summary="A" * 200,
        solutions=("step",),
    )
    short = err.short(40)
    assert len(short) <= 40
    assert short.endswith("...")


def test_extract_ffmpeg_error_hint():
    lines = [
        "frame=1",
        "configuration: --enable-libx264",
        "Error while decoding stream #0:0: Invalid data found when processing input",
    ]
    hint = extract_ffmpeg_error_hint(lines)
    assert "Invalid data" in hint


def test_unknown_still_has_generic_solutions():
    err = classify_error("something completely unexpected happened in the pipeline")
    assert err.code == "unknown"
    assert err.solutions
    assert "troubleshooting" in err.format().lower() or "FFmpeg" in err.format()


def test_reclassify_already_enriched_message():
    enriched = format_actionable_error("Unknown encoder 'aac_at'")
    again = classify_error(enriched)
    assert again.code == "unsupported_encoder"
    assert "What to try:" in again.format()


def test_smoke_mapped_message_snippets():
    """Sanity: key user-facing phrases appear for the milestone failure modes."""
    cases = {
        "ffmpeg_missing": ("FFmpeg not found", "PATH"),
        "disk_full": ("No space left on device", "Free disk"),
        "permission_denied": ("not writable", "output folder"),
        "corrupt_input": ("Invalid data found when processing input", "Re-download"),
        "unsupported_encoder": ("Unknown encoder 'libvpx-vp9'", "ffmpeg -encoders"),
    }
    for code, (raw, needle) in cases.items():
        text = format_actionable_error(raw)
        assert classify_error(raw).code == code
        assert needle.lower() in text.lower()
