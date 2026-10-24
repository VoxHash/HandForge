"""Actionable conversion/runtime error messages for HandForge.

Maps common FFmpeg, filesystem, and HandForge failure modes to a short
summary plus concrete next steps. Used by the orchestrator, CLI, and GUI
so users see the same guidance wherever an error surfaces.
"""

from __future__ import annotations

import errno
import re
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple, Union


@dataclass(frozen=True)
class ActionableError:
    """Structured user-facing failure with follow-up steps."""

    code: str
    title: str
    summary: str
    solutions: Tuple[str, ...]
    raw: str = ""

    def format(
        self,
        *,
        include_solutions: bool = True,
        include_raw: bool = False,
        max_raw: int = 240,
    ) -> str:
        """Render a multi-line message suitable for CLI stderr or GUI dialogs."""
        parts = [self.summary.rstrip()]
        if include_solutions and self.solutions:
            parts.append("")
            parts.append("What to try:")
            for i, step in enumerate(self.solutions, start=1):
                parts.append(f"  {i}. {step}")
        if include_raw and self.raw:
            snippet = self.raw.strip()
            if len(snippet) > max_raw:
                snippet = snippet[: max_raw - 3].rstrip() + "..."
            if snippet and snippet not in self.summary:
                parts.append("")
                parts.append(f"Details: {snippet}")
        return "\n".join(parts)

    def short(self, max_len: int = 80) -> str:
        """One-line form for table status / tray notifications."""
        text = self.summary.strip().replace("\n", " ")
        if len(text) <= max_len:
            return text
        return text[: max_len - 3].rstrip() + "..."


# Ordered rules: first match wins. Patterns are searched case-insensitively
# against the combined haystack (message + exception text + stderr).
_RULES: Tuple[Tuple[str, str, str, Tuple[str, ...], Tuple[str, ...]], ...] = (
    # code, title, summary, solutions, patterns
    (
        "ffmpeg_missing",
        "FFmpeg not found",
        "FFmpeg was not found on this system (or could not be started).",
        (
            "Install FFmpeg and ensure `ffmpeg` is on your PATH (`ffmpeg -version`).",
            "Linux: install via your package manager (e.g. `sudo pacman -S ffmpeg` or `sudo apt install ffmpeg`).",
            "macOS: `brew install ffmpeg` (Apple Silicon: ensure `/opt/homebrew/bin` is on PATH).",
            "Windows: install a build from https://ffmpeg.org/download.html and restart the terminal.",
            "Restart HandForge after changing PATH.",
        ),
        (
            r"ffmpeg not found",
            r"failed to start ffmpeg",
            r"no such file or directory: ['\"]?ffmpeg",
            r"cannot find.*ffmpeg",
            r"\[errno 2\].*ffmpeg",
        ),
    ),
    (
        "disk_full",
        "Disk full",
        "The output disk has no space left (or the quota is exhausted).",
        (
            "Free disk space on the volume that holds the output folder.",
            "Choose a different output directory on a drive with more free space.",
            "Delete unfinished/partial outputs in the destination folder, then retry.",
        ),
        (
            r"no space left",
            r"enospc",
            r"disk (?:is )?full",
            r"not enough space",
            r"quota exceeded",
        ),
    ),
    (
        "permission_denied",
        "Permission denied",
        "HandForge could not write to the output location (permission denied).",
        (
            "Choose an output folder you own (for example ~/HandForge_Output).",
            "Fix write permission on the folder (`chmod u+w <dir>` on Linux/macOS).",
            "If overwriting an existing file, make that file writable or enable rename/skip in Preferences.",
            "Avoid system-protected paths (/usr, /System, Program Files) as destinations.",
        ),
        (
            r"permission denied",
            r"permission error",
            r"not writable",
            r"cannot (?:create|write).*output",
            r"operation not permitted",
            r"access is denied",
            r"eacces",
        ),
    ),
    (
        "source_missing",
        "Source file missing",
        "The input file could not be found (moved, renamed, or deleted).",
        (
            "Confirm the file still exists at the original path.",
            "Re-add the file to the queue from its current location.",
            "Check that network/removable drives are still mounted.",
        ),
        (
            r"source file not found",
            r"input not found",
            r"no such file or directory",
            r"error opening input",
            r"does not exist",
        ),
    ),
    (
        "unsupported_encoder",
        "Encoder / codec unavailable",
        "FFmpeg does not have the requested encoder or codec in this build.",
        (
            "Pick a different output format or codec in HandForge (e.g. H.264 / AAC / MP3).",
            "Install a fuller FFmpeg build that includes the encoder (libx264, libx265, libvpx, …).",
            "Check available encoders: `ffmpeg -encoders`.",
            "Disable HEVC / exotic codecs if your build lacks them.",
        ),
        (
            r"unknown encoder",
            r"encoder ['\"]?\w+['\"]? not found",
            r"could not find encoder",
            r"encoder not found",
            r"codec not currently supported",
            r"unknown encoder['\"]?",
            r"error initializing output stream.*encoder",
            r"function not implemented.*encoder",
        ),
    ),
    (
        "unsupported_decoder",
        "Input codec unsupported",
        "FFmpeg cannot decode this input (missing decoder or exotic codec).",
        (
            "Try converting with a different tool first, or remux to a common container.",
            "Install an FFmpeg build with broader decoder support.",
            "Check: `ffmpeg -decoders` and compare with the file's codecs (`ffprobe -show_streams`).",
        ),
        (
            r"unknown decoder",
            r"decoder ['\"]?\w+['\"]? not found",
            r"could not find codec parameters",
            r"error while opening decoder",
            r"unsupported codec",
        ),
    ),
    (
        "unsupported_muxer",
        "Output format unsupported",
        "FFmpeg cannot write this container/format with the current settings.",
        (
            "Choose a different output format (mp4, mkv, mp3, m4a, …).",
            "Verify muxers: `ffmpeg -muxers`.",
            "For MP4 + subtitles, prefer mov_text or use MKV instead.",
        ),
        (
            r"unknown format",
            r"muxer.*not found",
            r"could not write header",
            r"invalid argument.*muxer",
            r"compatible with.*codec.*not currently supported in container",
        ),
    ),
    (
        "corrupt_input",
        "Corrupt or unreadable input",
        "The input file looks corrupt, truncated, or not a valid media stream.",
        (
            "Play the file in another player; if it fails there too, the source is bad.",
            "Re-download or restore the file from a backup.",
            "Try remuxing first: `ffmpeg -i input -c copy fixed.mkv`.",
            "Skip this file and continue the rest of the batch.",
        ),
        (
            r"invalid data found",
            r"moov atom not found",
            r"error while decoding",
            r"corrupt",
            r"truncated",
            r"invalid nal",
            r"error reading header",
            r"partial file",
            r"unexpected end of file",
        ),
    ),
    (
        "filter_graph",
        "Filter / processing error",
        "FFmpeg failed while applying filters (normalize, fade, crop, trim, …).",
        (
            "Disable loudness normalize / fade / crop / trim and retry.",
            "Check that trim/crop ranges fall inside the media duration.",
            "Clear custom FFmpeg args in the job or Preferences if you set any.",
        ),
        (
            r"error reinitializing filters",
            r"error applying option",
            r"filter.*failed",
            r"invalid.*filter",
            r"no such filter",
            r"cannot find a matching stream",
        ),
    ),
    (
        "missing_video",
        "Missing video in output",
        "Conversion finished but the output has no usable video stream.",
        (
            "Confirm the source actually contains video (`ffprobe -show_streams`).",
            "Do not enable extract-audio-only when you need video output.",
            "Retry with a different container (MKV) or codec (H.264).",
        ),
        (
            r"no video stream",
            r"video stream may be missing",
            r"video was not included",
        ),
    ),
    (
        "output_incomplete",
        "Output incomplete",
        "Conversion reported success but the output file is missing or too small.",
        (
            "Check free disk space and write permissions on the output folder.",
            "Retry the job; if it fails again, inspect the conversion log for FFmpeg errors.",
            "Try a simpler preset (e.g. MP3 CBR or H.264 MP4) to isolate the issue.",
        ),
        (
            r"output file not found",
            r"output file is too small",
            r"conversion may have failed",
        ),
    ),
    (
        "timeout",
        "Conversion timed out",
        "The conversion was stopped after running too long (1 hour limit).",
        (
            "Retry with a shorter clip or lower resolution/bitrate.",
            "Reduce parallel jobs so each encode gets more CPU.",
            "Check that the source is not an endless/live stream.",
        ),
        (
            r"timed out",
            r"conversion timed out",
        ),
    ),
    (
        "stopped",
        "Stopped",
        "Conversion was stopped by the user.",
        (
            "Press Start again to resume remaining queued jobs.",
        ),
        (
            r"stopped by user",
        ),
    ),
)

_COMPILED: Tuple[Tuple[str, str, str, Tuple[str, ...], Tuple[re.Pattern[str], ...]], ...] = tuple(
    (
        code,
        title,
        summary,
        solutions,
        tuple(re.compile(p, re.IGNORECASE) for p in patterns),
    )
    for code, title, summary, solutions, patterns in _RULES
)

_GENERIC = ActionableError(
    code="unknown",
    title="Conversion failed",
    summary="The conversion failed.",
    solutions=(
        "Open the conversion log (GUI: click Status or View Log) and read the last FFmpeg lines.",
        "Confirm FFmpeg works: `ffmpeg -version`.",
        "Retry with a simpler format (WAV / MP3 / H.264 MP4).",
        "See docs/troubleshooting.md for common fixes.",
    ),
)


def _exception_text(exc: Optional[BaseException]) -> str:
    if exc is None:
        return ""
    parts = [type(exc).__name__, str(exc)]
    if isinstance(exc, OSError) and exc.errno is not None:
        parts.append(f"errno={exc.errno}")
        try:
            parts.append(errno.errorcode.get(exc.errno, ""))
        except Exception:
            pass
    return " ".join(p for p in parts if p)


def _haystack(
    message: str = "",
    *,
    stderr: str = "",
    exc: Optional[BaseException] = None,
) -> str:
    return "\n".join(
        p for p in (message or "", stderr or "", _exception_text(exc)) if p
    )


def classify_error(
    message: str = "",
    *,
    stderr: str = "",
    exc: Optional[BaseException] = None,
) -> ActionableError:
    """Map a raw failure string/exception to an ActionableError."""
    text = _haystack(message, stderr=stderr, exc=exc)
    lowered = text.lower()

    # Prefer errno-based classification when available.
    if isinstance(exc, OSError):
        if exc.errno in (errno.ENOSPC,):
            return _match_by_code("disk_full", text)
        if exc.errno in (errno.EACCES, errno.EPERM):
            return _match_by_code("permission_denied", text)

    for code, title, summary, solutions, patterns in _COMPILED:
        if any(p.search(text) for p in patterns):
            return _build_matched(
                code, title, summary, solutions, message, stderr
            )

    # Re-entry: already-enriched messages (GUI/CLI) still carry our title/summary.
    for code, title, summary, solutions, _patterns in _COMPILED:
        if title.lower() in lowered or summary.lower() in lowered:
            return _build_matched(
                code, title, summary, solutions, message, stderr
            )

    # Fall through: keep the original message as the summary when useful.
    # If this is already an enriched multi-line message, use the first line only.
    raw_message = (message or "").strip()
    if "What to try:" in raw_message:
        summary = raw_message.splitlines()[0].strip()
    else:
        summary = raw_message or (stderr or "").strip() or _GENERIC.summary
    # Prefer last meaningful FFmpeg-looking line from stderr.
    if stderr and (
        not raw_message or raw_message.lower().startswith("conversion failed")
    ):
        line = _last_interesting_line(stderr)
        if line:
            summary = line
    if len(summary) > 300:
        summary = summary[:297].rstrip() + "..."
    if summary and not summary.endswith("."):
        summary = summary + "."
    return ActionableError(
        code=_GENERIC.code,
        title=_GENERIC.title,
        summary=summary or _GENERIC.summary,
        solutions=_GENERIC.solutions,
        raw=_best_raw(message, stderr),
    )


def _build_matched(
    code: str,
    title: str,
    summary: str,
    solutions: Tuple[str, ...],
    message: str,
    stderr: str,
) -> ActionableError:
    summary_out = summary
    # Keep path-specific permission/source hints when present.
    if code == "permission_denied" and message.strip():
        first = message.strip().splitlines()[0]
        if (
            "permission" in first.lower()
            or "writable" in first.lower()
            or "cannot" in first.lower()
        ):
            summary_out = first if first.endswith(".") else first + "."
    if code == "source_missing" and message.strip():
        first = message.strip().splitlines()[0]
        if "not found" in first.lower() or "input" in first.lower():
            summary_out = first if first.endswith(".") else first + "."
    return ActionableError(
        code=code,
        title=title,
        summary=summary_out,
        solutions=solutions,
        raw=_best_raw(message, stderr),
    )


def _match_by_code(code: str, text: str) -> ActionableError:
    for c, title, summary, solutions, _patterns in _COMPILED:
        if c == code:
            return ActionableError(
                code=c,
                title=title,
                summary=summary,
                solutions=solutions,
                raw=text.strip()[:400],
            )
    return _GENERIC


def _best_raw(message: str, stderr: str) -> str:
    for candidate in (stderr, message):
        line = _last_interesting_line(candidate or "")
        if line:
            return line
    return (message or stderr or "").strip()[:400]


def _last_interesting_line(text: str) -> str:
    if not text:
        return ""
    keywords = ("error", "failed", "invalid", "denied", "not found", "unable", "cannot")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    interesting = [
        ln
        for ln in lines
        if any(k in ln.lower() for k in keywords) and not ln.lower().startswith("frame=")
    ]
    if interesting:
        return interesting[-1][:400]
    return lines[-1][:400] if lines else ""


def format_actionable_error(
    message: str = "",
    *,
    stderr: str = "",
    exc: Optional[BaseException] = None,
    include_solutions: bool = True,
    include_raw: bool = False,
) -> str:
    """Classify then format — primary helper for orchestrator / CLI / GUI."""
    err = classify_error(message, stderr=stderr, exc=exc)
    return err.format(
        include_solutions=include_solutions,
        include_raw=include_raw,
    )


def extract_ffmpeg_error_hint(stderr_lines: Union[str, Sequence[str]]) -> str:
    """Pick the best single-line hint from FFmpeg stderr for classification."""
    if isinstance(stderr_lines, str):
        return _last_interesting_line(stderr_lines)
    return _last_interesting_line("\n".join(stderr_lines))
