"""Headless command-line interface for HandForge batch conversion.

Reuses the same Orchestrator / Worker / FFmpeg stack as the GUI.
Requires a Qt event loop (QCoreApplication) but no window or DISPLAY.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import __version__
from .core.models import Job
from .core.orchestrator import Orchestrator
from .core.presets import (
    BUILTIN_PRESETS,
    all_presets,
    apply_template,
    export_presets,
    export_template_library,
    get_preset,
    import_presets,
    known_preset_names,
    list_template_categories,
    list_templates,
)
from .core.settings import load_settings
from .util.ffmpeg import find_ffmpeg, is_audio_file, is_video_file


EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2


def _default_output_dir() -> str:
    if os.name == "nt":
        return os.path.join(os.environ.get("USERPROFILE", ""), "HandForge_Output")
    return os.path.expanduser("~/HandForge_Output")


def collect_inputs(paths: Sequence[str]) -> List[str]:
    """Expand files and directories into a sorted list of media paths."""
    found: List[str] = []
    seen = set()
    for raw in paths:
        path = Path(raw).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Input not found: {raw}")
        if path.is_file():
            candidates = [path]
        else:
            candidates = sorted(p for p in path.rglob("*") if p.is_file())
        for candidate in candidates:
            resolved = str(candidate.resolve())
            if resolved in seen:
                continue
            if is_audio_file(resolved) or is_video_file(resolved):
                seen.add(resolved)
                found.append(resolved)
    return found


def resolve_conversion_options(args: argparse.Namespace) -> Dict[str, Any]:
    """Build conversion options from --preset and/or explicit flags."""
    options: Dict[str, Any] = {}
    if args.preset:
        try:
            options.update(get_preset(args.preset))
        except KeyError as exc:
            known = ", ".join(known_preset_names())
            raise ValueError(
                f"Unknown preset: {exc.args[0]!r}\nKnown presets: {known}"
            ) from exc

    if args.format:
        options["format"] = args.format
    if args.mode:
        options["mode"] = args.mode
    if args.bitrate is not None:
        options["bitrate"] = args.bitrate
    if args.vbrq is not None:
        options["vbrq"] = args.vbrq
    if args.video_codec:
        options["video_codec"] = args.video_codec
    if args.video_quality is not None:
        options["video_quality"] = args.video_quality
    if args.video_bitrate is not None:
        options["video_bitrate"] = args.video_bitrate
    if getattr(args, "extract_audio", False):
        options["extract_audio_only"] = True

    if "format" not in options:
        options["format"] = "mp3"
    if "mode" not in options:
        options["mode"] = "CBR"
    if options["mode"] == "CBR" and not options.get("bitrate") and not options.get(
        "video_codec"
    ):
        options.setdefault("bitrate", "192")
    return options


def build_job(
    src: str,
    dst_dir: str,
    options: Dict[str, Any],
    settings: Dict[str, Any],
    meta: Optional[Dict[str, Optional[str]]] = None,
) -> Job:
    """Create a Job from resolved options (same mapping as the GUI start path)."""
    dst_format = options.get("format", "mp3")
    src_is_video = is_video_file(src)
    dst_is_video = is_video_file(f"dummy.{dst_format}")

    meta = meta or {}
    job = Job(
        src=src,
        dst_dir=dst_dir,
        format=dst_format,
        mode=options.get("mode", "CBR"),
        bitrate=options.get("bitrate"),
        vbrq=options.get("vbrq"),
        prefer_external_cover=settings.get("prefer_external_cover", False),
        normalize_lufs=settings.get("normalize_lufs", False),
        target_lufs=settings.get("target_lufs", -14.0),
        meta_title=meta.get("title"),
        meta_artist=meta.get("artist"),
        meta_album=meta.get("album"),
        meta_year=meta.get("year"),
        meta_genre=meta.get("genre"),
        meta_track=meta.get("track"),
        copy_meta=True,
    )

    if options.get("extract_audio_only"):
        job.extract_audio_only = True
    elif src_is_video and not dst_is_video:
        job.extract_audio_only = True
    elif src_is_video and dst_is_video:
        job.extract_audio_only = False
        job.video_codec = options.get("video_codec")
        job.video_bitrate = options.get("video_bitrate")
        job.video_quality = options.get("video_quality")
        job.resolution = options.get("resolution")
        job.fps = options.get("fps")
        if options.get("reduce_size"):
            job.reduce_size = True
            job.size_reduction_factor = options.get("size_reduction_factor", 7.0)
            job.use_hevc = bool(options.get("use_hevc", True))
            job.two_pass = bool(options.get("two_pass", False))

    return job


def ensure_qt_app(argv: Optional[List[str]] = None):
    """Return a QCoreApplication suitable for headless Orchestrator use."""
    # Import Qt only when running conversions (list-presets needs no event loop).
    from PyQt6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    if app is None:
        # Avoid Qt platform plugins needing a real display.
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QCoreApplication(argv if argv is not None else sys.argv[:1])
    return app


def run_batch(
    jobs: List[Job],
    settings: Dict[str, Any],
    *,
    quiet: bool = False,
    verbose: bool = False,
) -> Tuple[int, int]:
    """Run jobs through Orchestrator; return (succeeded, failed)."""
    from PyQt6.QtCore import QCoreApplication

    app = ensure_qt_app()
    orch = Orchestrator(
        threads_per_job=1,
        max_parallel=int(settings.get("parallel", 2) or 1),
    )
    orch.set_settings(settings)

    total = len(jobs)
    completed = 0
    succeeded = 0
    failed = 0
    # Map worker id -> (index, basename) once started
    job_labels: Dict[int, Tuple[int, str]] = {}
    start_order = {id(job): i for i, job in enumerate(jobs, start=1)}

    def on_started(wid: int, file_path: str) -> None:
        # Match label by src; fall back to completion order index
        label_idx = next(
            (start_order[id(j)] for j in jobs if j.src == file_path),
            completed + 1,
        )
        job_labels[wid] = (label_idx, os.path.basename(file_path))
        if not quiet:
            print(
                f"[{label_idx}/{total}] {os.path.basename(file_path)}  started",
                file=sys.stderr,
                flush=True,
            )

    def on_progress(
        wid: int,
        progress: float,
        elapsed: float,
        eta: float,
        speed: str,
        _peak: str,
        _true_peak: str,
    ) -> None:
        if quiet:
            return
        idx, name = job_labels.get(wid, (wid, f"job-{wid}"))
        print(
            f"[{idx}/{total}] {name}  {progress:5.1f}%  "
            f"elapsed={elapsed:.1f}s  eta={eta:.1f}s  speed={speed}",
            file=sys.stderr,
            flush=True,
        )

    def on_log(wid: int, line: str) -> None:
        if verbose and not quiet:
            idx, name = job_labels.get(wid, (wid, f"job-{wid}"))
            print(f"[{idx}/{total}] {name}  | {line}", file=sys.stderr, flush=True)

    def on_done(wid: int, success: bool, message: str, output_path: str) -> None:
        nonlocal completed, succeeded, failed
        completed += 1
        idx, name = job_labels.get(wid, (wid, f"job-{wid}"))
        if success:
            succeeded += 1
            dest = output_path or ""
            if not quiet:
                print(
                    f"[{idx}/{total}] {name}  ok  {dest}",
                    file=sys.stderr,
                    flush=True,
                )
            # Always emit output paths on stdout for scripting (including --quiet).
            if dest:
                print(dest, flush=True)
        else:
            failed += 1
            print(
                f"[{idx}/{total}] {name}  FAIL  {message}",
                file=sys.stderr,
                flush=True,
            )
        if completed >= total and not orch.job_queue and not orch.workers:
            QCoreApplication.instance().quit()

    orch.sig_worker_started.connect(on_started)
    orch.sig_worker_progress.connect(on_progress)
    orch.sig_worker_log.connect(on_log)
    orch.sig_worker_done.connect(on_done)

    orch.enqueue(list(jobs))
    if total == 0:
        return 0, 0
    app.exec()
    return succeeded, failed


def _format_preset_line(name: str, tag: str, preset: Dict[str, Any]) -> str:
    fmt = preset.get("format", "?")
    mode = preset.get("mode", "")
    rate = preset.get("bitrate") or preset.get("vbrq") or ""
    extra = f"  {mode}" if mode else ""
    if rate:
        extra += f"  {rate}"
    return f"{name}\t[{tag}]\tformat={fmt}{extra}"


def cmd_list_presets(args: argparse.Namespace) -> int:
    presets = all_presets()
    builtin_names = set(BUILTIN_PRESETS)
    for name in sorted(presets.keys()):
        tag = "builtin" if name in builtin_names else "custom"
        print(_format_preset_line(name, tag, presets[name]))
    if getattr(args, "include_templates", False):
        for template in list_templates():
            name = str(template.get("name") or template.get("id"))
            print(
                _format_preset_line(
                    name, "template", template.get("options") or {}
                )
            )
    return EXIT_OK


def cmd_list_templates(args: argparse.Namespace) -> int:
    templates = list_templates(category=args.category)
    if not templates:
        if args.category:
            known = ", ".join(list_template_categories())
            print(
                f"No templates in category {args.category!r}. "
                f"Known categories: {known}",
                file=sys.stderr,
            )
            return EXIT_USAGE
        print("No templates found.", file=sys.stderr)
        return EXIT_FAIL
    for template in templates:
        tid = template.get("id", "")
        name = template.get("name", "")
        cat = template.get("category", "")
        opts = template.get("options") or {}
        fmt = opts.get("format", "?")
        desc = (template.get("description") or "").strip()
        print(f"{tid}\t{name}\t[{cat}]\tformat={fmt}")
        if args.verbose and desc:
            print(f"  {desc}")
    return EXIT_OK


def cmd_apply_template(args: argparse.Namespace) -> int:
    try:
        saved_name, options = apply_template(
            args.template,
            as_name=args.as_name,
            overwrite=args.overwrite,
        )
    except KeyError as exc:
        known = ", ".join(t["id"] for t in list_templates())
        print(
            f"Unknown template: {exc.args[0]!r}\nKnown ids: {known}",
            file=sys.stderr,
        )
        return EXIT_USAGE
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_FAIL
    print(
        f"Applied template → custom preset {saved_name!r} "
        f"(format={options.get('format')})"
    )
    return EXIT_OK


def cmd_export_presets(args: argparse.Namespace) -> int:
    try:
        if args.templates:
            path = export_template_library(args.path)
            print(f"Exported template library to {path}")
        else:
            path = export_presets(
                args.path, include_builtin=args.include_builtin
            )
            print(f"Exported presets to {path}")
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_FAIL
    return EXIT_OK


def cmd_import_presets(args: argparse.Namespace) -> int:
    try:
        customs = import_presets(args.path, replace=args.replace)
    except FileNotFoundError:
        print(f"File not found: {args.path}", file=sys.stderr)
        return EXIT_USAGE
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_FAIL
    print(f"Imported presets ({len(customs)} custom preset(s) now saved).")
    return EXIT_OK


def cmd_convert(args: argparse.Namespace) -> int:
    if not find_ffmpeg():
        print(
            "FFmpeg not found on PATH. Install FFmpeg and retry.",
            file=sys.stderr,
        )
        return EXIT_FAIL

    try:
        inputs = collect_inputs(args.inputs)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE

    if not inputs:
        print("No supported media files found in the given paths.", file=sys.stderr)
        return EXIT_USAGE

    try:
        options = resolve_conversion_options(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE

    settings = load_settings()
    if args.parallel is not None:
        settings["parallel"] = max(1, int(args.parallel))
    if args.no_adaptive:
        settings["adaptive_parallel"] = False

    out_dir = args.output_dir or settings.get("output_dir") or _default_output_dir()
    out_dir = os.path.expanduser(str(out_dir))
    os.makedirs(out_dir, mode=0o755, exist_ok=True)

    if args.on_exists:
        settings["on_exists"] = args.on_exists

    meta = {
        "title": args.title,
        "artist": args.artist,
        "album": args.album,
        "year": args.year,
        "genre": args.genre,
        "track": args.track,
    }

    jobs = [
        build_job(src, out_dir, options, settings, meta=meta) for src in inputs
    ]

    if not args.quiet:
        print(
            f"HandForge CLI {__version__}: {len(jobs)} job(s) → {out_dir} "
            f"(format={options.get('format')}, parallel={settings.get('parallel')})",
            file=sys.stderr,
            flush=True,
        )

    _ok, failed = run_batch(
        jobs, settings, quiet=args.quiet, verbose=args.verbose
    )
    if failed:
        print(f"Completed with {failed} failure(s).", file=sys.stderr)
        return EXIT_FAIL
    if not args.quiet:
        print(f"Completed {len(jobs)} conversion(s) successfully.", file=sys.stderr)
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="handforge",
        description="HandForge headless batch converter (FFmpeg via shared orchestrator).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"HandForge {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser(
        "list-presets",
        help="List built-in and custom presets",
    )
    p_list.add_argument(
        "--include-templates",
        action="store_true",
        help="Also list curated library templates",
    )
    p_list.set_defaults(func=cmd_list_presets)

    p_tmpl = sub.add_parser(
        "list-templates",
        help="Browse the curated preset template library",
    )
    p_tmpl.add_argument(
        "--category",
        help="Filter by category (Podcast, Speech, Music, Archive, Video)",
    )
    p_tmpl.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Include template descriptions",
    )
    p_tmpl.set_defaults(func=cmd_list_templates)

    p_apply = sub.add_parser(
        "apply-template",
        help="Install a library template into custom presets",
    )
    p_apply.add_argument(
        "template",
        help="Template id or display name (see list-templates)",
    )
    p_apply.add_argument(
        "--as",
        dest="as_name",
        help="Save under a custom preset name",
    )
    p_apply.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing custom preset with the same name",
    )
    p_apply.set_defaults(func=cmd_apply_template)

    p_export = sub.add_parser(
        "export-presets",
        help="Export custom presets (or the template library) to JSON",
    )
    p_export.add_argument("path", help="Output JSON path")
    p_export.add_argument(
        "--include-builtin",
        action="store_true",
        help="Include built-in presets in the export",
    )
    p_export.add_argument(
        "--templates",
        action="store_true",
        help="Export the curated template library instead of custom presets",
    )
    p_export.set_defaults(func=cmd_export_presets)

    p_import = sub.add_parser(
        "import-presets",
        help="Import presets from a JSON file into custom presets",
    )
    p_import.add_argument("path", help="Input JSON path")
    p_import.add_argument(
        "--replace",
        action="store_true",
        help="Replace all custom presets (default: merge / overwrite by name)",
    )
    p_import.set_defaults(func=cmd_import_presets)

    p_conv = sub.add_parser(
        "convert",
        help="Convert one or more media files or directories",
    )
    p_conv.add_argument(
        "inputs",
        nargs="+",
        help="Input file(s) and/or directories (directories are scanned recursively)",
    )
    p_conv.add_argument(
        "-o",
        "--output-dir",
        help="Output directory (default: settings or ~/HandForge_Output)",
    )
    p_conv.add_argument(
        "-p",
        "--preset",
        help=(
            'Named preset or template id/name, e.g. "MP3 192k" '
            'or "podcast-aac-128"'
        ),
    )
    p_conv.add_argument(
        "-f",
        "--format",
        help="Output format/extension (overrides preset format)",
    )
    p_conv.add_argument(
        "--mode",
        choices=["CBR", "VBR", "Lossless"],
        help="Audio encoding mode",
    )
    p_conv.add_argument("--bitrate", help="Audio bitrate (e.g. 192)")
    p_conv.add_argument("--vbrq", help="VBR quality value")
    p_conv.add_argument("--video-codec", help="Video codec (e.g. libx264)")
    p_conv.add_argument("--video-quality", help="Video CRF/quality value")
    p_conv.add_argument("--video-bitrate", help="Video bitrate (e.g. 5000)")
    p_conv.add_argument(
        "--extract-audio",
        action="store_true",
        help="Extract audio only from video sources",
    )
    p_conv.add_argument(
        "--parallel",
        type=int,
        help="Max parallel conversions (hard ceiling)",
    )
    p_conv.add_argument(
        "--no-adaptive",
        action="store_true",
        help="Disable adaptive parallel scheduling",
    )
    p_conv.add_argument(
        "--on-exists",
        choices=["overwrite", "skip", "rename"],
        help="Behavior when output file already exists",
    )
    p_conv.add_argument("--title", help="Metadata title")
    p_conv.add_argument("--artist", help="Metadata artist")
    p_conv.add_argument("--album", help="Metadata album")
    p_conv.add_argument("--year", help="Metadata year")
    p_conv.add_argument("--genre", help="Metadata genre")
    p_conv.add_argument("--track", help="Metadata track number")
    p_conv.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only print output paths (stdout) and errors (stderr)",
    )
    p_conv.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print FFmpeg log lines on stderr",
    )
    p_conv.set_defaults(func=cmd_convert)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
