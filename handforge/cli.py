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
from .util.cloud import (
    cleanup_staging,
    format_cloud_status,
    prepare_inputs,
    prepare_output,
    push_output,
)
from .util.errors import format_actionable_error
from .util.ffmpeg import find_ffmpeg, is_audio_file, is_video_file
from .util.hwaccel import (
    HW_PREFERENCES,
    detect_available_backends,
    format_detection_report,
    normalize_hw_preference,
)


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
    if getattr(args, "preset", None):
        try:
            options.update(get_preset(args.preset))
        except KeyError as exc:
            known = ", ".join(known_preset_names())
            raise ValueError(
                f"Unknown preset: {exc.args[0]!r}\nKnown presets: {known}"
            ) from exc

    if getattr(args, "format", None):
        options["format"] = args.format
    if getattr(args, "mode", None):
        options["mode"] = args.mode
    if getattr(args, "bitrate", None) is not None:
        options["bitrate"] = args.bitrate
    if getattr(args, "vbrq", None) is not None:
        options["vbrq"] = args.vbrq
    if getattr(args, "video_codec", None):
        options["video_codec"] = args.video_codec
    if getattr(args, "video_quality", None) is not None:
        options["video_quality"] = args.video_quality
    if getattr(args, "video_bitrate", None) is not None:
        options["video_bitrate"] = args.video_bitrate
    if getattr(args, "hw_accel", None):
        options["hw_accel"] = normalize_hw_preference(args.hw_accel)
    if getattr(args, "extract_audio", False):
        options["extract_audio_only"] = True

    # Advanced audio filters — CLI flags override settings when present
    if getattr(args, "eq", False):
        options["eq_enabled"] = True
    if getattr(args, "eq_bass", None) is not None:
        options["eq_enabled"] = True
        options["eq_bass"] = args.eq_bass
    if getattr(args, "eq_mid", None) is not None:
        options["eq_enabled"] = True
        options["eq_mid"] = args.eq_mid
    if getattr(args, "eq_treble", None) is not None:
        options["eq_enabled"] = True
        options["eq_treble"] = args.eq_treble
    if getattr(args, "compressor", False):
        options["compressor_enabled"] = True
    if getattr(args, "compressor_threshold", None) is not None:
        options["compressor_enabled"] = True
        options["compressor_threshold"] = args.compressor_threshold
    if getattr(args, "compressor_ratio", None) is not None:
        options["compressor_enabled"] = True
        options["compressor_ratio"] = args.compressor_ratio
    if getattr(args, "limiter", False):
        options["limiter_enabled"] = True
    if getattr(args, "limiter_limit", None) is not None:
        options["limiter_enabled"] = True
        options["limiter_limit"] = args.limiter_limit
    if getattr(args, "denoise", False):
        options["denoise_enabled"] = True
    if getattr(args, "denoise_nr", None) is not None:
        options["denoise_enabled"] = True
        options["denoise_nr"] = args.denoise_nr
    if getattr(args, "denoise_nf", None) is not None:
        options["denoise_enabled"] = True
        options["denoise_nf"] = args.denoise_nf

    # Advanced video filters — CLI flags override settings when present
    if getattr(args, "video_color", False):
        options["video_color_enabled"] = True
    if getattr(args, "brightness", None) is not None:
        options["video_color_enabled"] = True
        options["video_brightness"] = args.brightness
    if getattr(args, "contrast", None) is not None:
        options["video_color_enabled"] = True
        options["video_contrast"] = args.contrast
    if getattr(args, "saturation", None) is not None:
        options["video_color_enabled"] = True
        options["video_saturation"] = args.saturation
    if getattr(args, "stabilize", False):
        options["video_stabilize_enabled"] = True
    if getattr(args, "stabilize_rx", None) is not None:
        options["video_stabilize_enabled"] = True
        options["video_stabilize_rx"] = args.stabilize_rx
    if getattr(args, "stabilize_ry", None) is not None:
        options["video_stabilize_enabled"] = True
        options["video_stabilize_ry"] = args.stabilize_ry

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

    def _af(key: str, default: Any) -> Any:
        if key in options:
            return options[key]
        return settings.get(key, default)

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
        eq_enabled=bool(_af("eq_enabled", False)),
        eq_bass=float(_af("eq_bass", 0.0)),
        eq_mid=float(_af("eq_mid", 0.0)),
        eq_treble=float(_af("eq_treble", 0.0)),
        compressor_enabled=bool(_af("compressor_enabled", False)),
        compressor_threshold=float(_af("compressor_threshold", 0.125)),
        compressor_ratio=float(_af("compressor_ratio", 4.0)),
        compressor_attack=float(_af("compressor_attack", 20.0)),
        compressor_release=float(_af("compressor_release", 250.0)),
        compressor_makeup=float(_af("compressor_makeup", 2.0)),
        limiter_enabled=bool(_af("limiter_enabled", False)),
        limiter_limit=float(_af("limiter_limit", 0.95)),
        limiter_attack=float(_af("limiter_attack", 5.0)),
        limiter_release=float(_af("limiter_release", 50.0)),
        denoise_enabled=bool(_af("denoise_enabled", False)),
        denoise_nr=float(_af("denoise_nr", 12.0)),
        denoise_nf=float(_af("denoise_nf", -50.0)),
        denoise_track_noise=bool(_af("denoise_track_noise", True)),
        video_color_enabled=bool(_af("video_color_enabled", False)),
        video_brightness=float(_af("video_brightness", 0.0)),
        video_contrast=float(_af("video_contrast", 1.0)),
        video_saturation=float(_af("video_saturation", 1.0)),
        video_stabilize_enabled=bool(_af("video_stabilize_enabled", False)),
        video_stabilize_rx=int(_af("video_stabilize_rx", 16)),
        video_stabilize_ry=int(_af("video_stabilize_ry", 16)),
        video_stabilize_edge=str(_af("video_stabilize_edge", "mirror")),
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
        if options.get("hw_accel"):
            job.hw_accel = options.get("hw_accel")
        elif settings.get("hw_accel"):
            job.hw_accel = settings.get("hw_accel")
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
    companion: bool = False,
    companion_host: Optional[str] = None,
    companion_port: Optional[int] = None,
    companion_token: Optional[str] = None,
    companion_lan: bool = False,
) -> Tuple[int, int]:
    """Run jobs through Orchestrator; return (succeeded, failed)."""
    from PyQt6.QtCore import QCoreApplication

    from .companion import QueueStatusHub
    from .companion.server import (
        companion_url,
        resolve_companion_bind,
        start_companion_from_settings,
    )
    from .util.analytics import (
        BatchAnalyticsSession,
        analytics_enabled,
        format_batch_summary,
    )

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
    analytics = (
        BatchAnalyticsSession.start(settings) if analytics_enabled(settings) else None
    )
    hub = QueueStatusHub()
    hub.attach(orch, app_label="HandForge CLI")
    companion_server = None
    if companion or settings.get("companion_enabled"):
        try:
            companion_server = start_companion_from_settings(
                hub,
                settings,
                host=companion_host,
                port=companion_port,
                token=companion_token,
                lan=companion_lan,
                force=True,
            )
            if companion_server is not None and not quiet:
                host, port, token = resolve_companion_bind(
                    settings,
                    host=companion_host,
                    port=companion_port,
                    token=companion_token,
                    lan=companion_lan,
                )
                print(
                    f"Companion monitor: {companion_url(host, port, token)}",
                    file=sys.stderr,
                    flush=True,
                )
        except (OSError, ValueError) as exc:
            print(f"Companion server failed: {exc}", file=sys.stderr)

    def on_started(wid: int, file_path: str) -> None:
        # Match label by src; fall back to completion order index
        label_idx = next(
            (start_order[id(j)] for j in jobs if j.src == file_path),
            completed + 1,
        )
        job_labels[wid] = (label_idx, os.path.basename(file_path))
        hub.on_started(wid, file_path)
        if analytics is not None:
            analytics.on_started(wid, file_path)
            analytics.note_parallel(len(orch.workers))
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
        hub.on_progress(wid, progress, elapsed, eta, speed, _peak, _true_peak)
        if analytics is not None:
            analytics.on_progress(wid, progress, elapsed, eta, speed)
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
        hub.on_done(wid, success, message, output_path)
        if analytics is not None:
            analytics.on_done(wid, success, message, output_path)
            analytics.note_parallel(len(orch.workers))
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
            # Orchestrator already enriches failures; keep multi-line solutions readable.
            first_line, *rest = (message or "Unknown error").splitlines()
            print(
                f"[{idx}/{total}] {name}  FAIL  {first_line}",
                file=sys.stderr,
                flush=True,
            )
            for line in rest:
                if line.strip():
                    print(f"  {line}", file=sys.stderr, flush=True)
        if completed >= total and not orch.job_queue and not orch.workers:
            QCoreApplication.instance().quit()

    orch.sig_worker_started.connect(on_started)
    orch.sig_worker_progress.connect(on_progress)
    orch.sig_worker_log.connect(on_log)
    orch.sig_worker_done.connect(on_done)

    orch.enqueue(list(jobs))
    if total == 0:
        if companion_server is not None:
            companion_server.stop()
        return 0, 0
    app.exec()
    if companion_server is not None:
        companion_server.stop()
    if analytics is not None and not analytics.finished:
        summary = analytics.finish(persist=True)
        # Always print analytics summary when the feature is enabled (even with --quiet).
        print(format_batch_summary(summary, detailed=verbose), file=sys.stderr)
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
    from .core.settings import load_custom_presets
    from .plugins import get_registry

    presets = all_presets()
    builtin_names = set(BUILTIN_PRESETS)
    plugin_names = set(get_registry().presets)
    custom_names = set(load_custom_presets())
    for name in sorted(presets.keys()):
        if name in custom_names:
            tag = "custom"
        elif name in plugin_names:
            tag = "plugin"
        elif name in builtin_names:
            tag = "builtin"
        else:
            tag = "custom"
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


def cmd_list_plugins(args: argparse.Namespace) -> int:
    """List discovered plugins and their contributions."""
    from .plugins import ensure_plugins_loaded, get_registry

    ensure_plugins_loaded(load_settings(), reload=True)
    registry = get_registry()
    plugins = registry.loaded_plugins
    if not plugins:
        print("No plugins loaded.")
        print(
            "Install under ~/.handforge/plugins/<name>/plugin.py, "
            "set HANDFORGE_PLUGIN_DIRS, or use entry points "
            "(group handforge.plugins).",
            file=sys.stderr,
        )
        return EXIT_OK
    for loaded in plugins:
        info = loaded.info
        status = "ok" if not loaded.errors else "error"
        print(
            f"{info.name}\tv={info.version}\t[{info.source}]\t{status}"
            + (f"\t{info.path}" if info.path else "")
        )
        if info.description:
            print(f"  {info.description}")
        for err in loaded.errors:
            print(f"  error: {err}", file=sys.stderr)
    if getattr(args, "verbose", False):
        presets = registry.presets
        print(
            f"presets={len(presets)} "
            f"pre_convert={len(registry.pre_convert_hooks)} "
            f"post_convert={len(registry.post_convert_hooks)}"
        )
        for name in sorted(presets):
            print(f"  preset: {name} → format={presets[name].get('format')}")
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


def cmd_list_hw_accel(args: argparse.Namespace) -> int:
    """Probe FFmpeg and print available hardware video encoders."""
    if not find_ffmpeg():
        print(
            format_actionable_error("FFmpeg not found on PATH"),
            file=sys.stderr,
        )
        return EXIT_FAIL
    probe = not getattr(args, "no_probe", False)
    info = detect_available_backends(probe=probe, force_refresh=True)
    print(format_detection_report(info))
    backends = info.get("backends") or {}
    if any(backends.values()):
        return EXIT_OK
    # No HW available is still a successful detection run.
    return EXIT_OK


def cmd_list_cloud(args: argparse.Namespace) -> int:
    """Show rclone availability/remotes and local cloud sync roots."""
    settings = load_settings()
    print(format_cloud_status(settings))
    return EXIT_OK


def cmd_list_analytics(args: argparse.Namespace) -> int:
    """Show local performance-analytics status and recent batches."""
    from .util.analytics import (
        BatchSummary,
        build_aggregate_report,
        format_aggregate_report,
        format_analytics_status,
        format_batch_summary,
        load_recent_batches,
    )

    settings = load_settings()
    print(format_analytics_status(settings))
    limit = int(getattr(args, "limit", 5) or 5)
    if getattr(args, "report", False):
        report = build_aggregate_report(limit=max(limit, 50))
        print()
        print(format_aggregate_report(report, detailed=bool(args.verbose)))
        return EXIT_OK
    recent = load_recent_batches(limit=limit)
    if not recent:
        return EXIT_OK
    print()
    for raw in reversed(recent):
        try:
            summary = BatchSummary(
                batch_id=str(raw.get("batch_id") or "?"),
                started_at=float(raw.get("started_at") or 0),
                ended_at=float(raw.get("ended_at") or 0),
                job_count=int(raw.get("job_count") or 0),
                succeeded=int(raw.get("succeeded") or 0),
                failed=int(raw.get("failed") or 0),
                wall_seconds=float(raw.get("wall_seconds") or 0),
                peak_parallel=int(raw.get("peak_parallel") or 0),
                parallel_setting=int(raw.get("parallel_setting") or 0),
                adaptive_parallel=bool(raw.get("adaptive_parallel", True)),
                total_bytes_in=int(raw.get("total_bytes_in") or 0),
                total_bytes_out=int(raw.get("total_bytes_out") or 0),
                mean_job_seconds=float(raw.get("mean_job_seconds") or 0),
                mean_speed_x=raw.get("mean_speed_x"),
                peak_speed_x=raw.get("peak_speed_x"),
                throughput_bps=raw.get("throughput_bps"),
                eta_mae_seconds=raw.get("eta_mae_seconds"),
                jobs=list(raw.get("jobs") or []),
            )
            print(format_batch_summary(summary, detailed=bool(args.verbose)))
            print()
        except (TypeError, ValueError):
            continue
    return EXIT_OK


def cmd_watch(args: argparse.Namespace) -> int:
    """Poll watch-folder directories and convert newly stable media files."""
    import time

    from .core.settings import save_seen_files
    from .util.watchfolder import (
        format_watchfolder_status,
        scan_once,
        watchfolder_dirs,
        watchfolder_interval,
        watchfolder_recursive,
    )

    if not find_ffmpeg():
        print(
            format_actionable_error("FFmpeg not found on PATH"),
            file=sys.stderr,
        )
        return EXIT_FAIL

    settings = load_settings()
    dirs: List[str] = []
    for d in list(getattr(args, "folders", None) or []) + list(
        getattr(args, "dir", None) or []
    ):
        text = str(Path(str(d)).expanduser())
        if text and text not in dirs:
            dirs.append(text)
    if not dirs:
        dirs = watchfolder_dirs(settings)
    if not dirs:
        print(
            "No watch folders configured. Pass one or more paths or set "
            "watchfolder_dirs in Preferences / settings.json.",
            file=sys.stderr,
        )
        print(format_watchfolder_status(settings), file=sys.stderr)
        return EXIT_USAGE

    if getattr(args, "parallel", None) is not None:
        settings["parallel"] = max(1, int(args.parallel))
    if getattr(args, "no_adaptive", False):
        settings["adaptive_parallel"] = False
    if getattr(args, "analytics", False):
        settings["performance_analytics"] = True
    if getattr(args, "no_analytics", False):
        settings["performance_analytics"] = False

    try:
        options = resolve_conversion_options(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE

    out_dir = (
        getattr(args, "output_dir", None)
        or settings.get("output_dir")
        or _default_output_dir()
    )
    out_dir = str(Path(str(out_dir)).expanduser())
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    interval = (
        float(args.interval)
        if getattr(args, "interval", None) is not None
        else watchfolder_interval(settings)
    )
    recursive = watchfolder_recursive(settings)
    if getattr(args, "no_recursive", False):
        recursive = False

    once = bool(getattr(args, "once", False))
    quiet = bool(getattr(args, "quiet", False))
    if not quiet:
        print(format_watchfolder_status({**settings, "watchfolder_dirs": dirs}))
        print(f"  output: {out_dir}")
        print(f"  polling every {interval:.1f}s" + (" (once)" if once else ""))
        if not once:
            print("  Ctrl+C to stop", file=sys.stderr)

    pending_fps: Dict[str, Dict[str, Any]] = {}
    total_fail = 0
    settle = float(getattr(args, "settle", 1.5) or 1.5)

    try:
        while True:
            # Seed fingerprints, wait for settle, then pick stable new files.
            _, seen_cache, pending_fps = scan_once(
                dirs,
                recursive=recursive,
                pending_fps=pending_fps,
                settle_seconds=settle,
            )
            time.sleep(max(0.2, settle))
            ready, seen_cache, pending_fps = scan_once(
                dirs,
                seen=seen_cache,
                recursive=recursive,
                pending_fps=pending_fps,
                settle_seconds=settle,
            )

            if ready:
                jobs = [
                    build_job(str(path), out_dir, options, settings, meta={})
                    for path in ready
                ]
                if not quiet:
                    print(
                        f"Watch-folder: converting {len(jobs)} new file(s)",
                        file=sys.stderr,
                    )
                _ok, fail = run_batch(
                    jobs,
                    settings,
                    quiet=quiet,
                    verbose=bool(getattr(args, "verbose", False)),
                )
                total_fail += fail
                for path in ready:
                    key = str(path.resolve())
                    if key in seen_cache:
                        seen_cache[key]["status"] = "processed"
                save_seen_files(seen_cache)

            if once:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        if not quiet:
            print("\nWatch-folder stopped.", file=sys.stderr)

    if total_fail:
        return EXIT_FAIL
    return EXIT_OK


def cmd_serve(args: argparse.Namespace) -> int:
    """Start the companion HTTP server with shared-workstation control."""
    import time

    from PyQt6.QtCore import QCoreApplication

    from .companion import QueueStatusHub, SessionController
    from .companion.server import (
        CompanionServer,
        companion_url,
        format_companion_status,
        generate_token,
        resolve_companion_bind,
    )

    settings = load_settings()
    settings["companion_enabled"] = True
    if getattr(args, "host", None):
        settings["companion_host"] = str(args.host).strip()
    if getattr(args, "port", None) is not None:
        settings["companion_port"] = int(args.port)
    if getattr(args, "token", None) is not None:
        settings["companion_token"] = str(args.token)
    lan = bool(getattr(args, "lan", False))
    if lan:
        settings["companion_host"] = "0.0.0.0"

    host, port, token = resolve_companion_bind(settings, lan=lan)
    # Shared control writes always need a token; mint one for localhost serve.
    if not token:
        token = generate_token()
    settings["companion_host"] = host
    settings["companion_port"] = port
    settings["companion_token"] = token

    app = ensure_qt_app()
    orch = Orchestrator(
        threads_per_job=1,
        max_parallel=int(settings.get("parallel", 2) or 1),
    )
    orch.set_settings(settings)
    hub = QueueStatusHub()
    controller = SessionController()
    pending: list = []

    from .core.queue_persist import (
        clear_queue_state,
        jobs_for_restore,
        load_queue_state,
        persist_live_queue,
    )

    restored = jobs_for_restore(load_queue_state(), require_existing=True)
    if restored:
        pending.extend(restored)
        print(
            f"Restored {len(restored)} job(s) from crash-safe queue "
            f"(~/.handforge/queue.json).",
            file=sys.stderr,
        )

    def _persist_serve() -> None:
        persist_live_queue(
            pending=pending,
            orchestrator=orch,
            session={
                "output_dir": str(settings.get("output_dir") or ""),
                "preset": "MP3 192k",
            },
        )

    def _serve_notify() -> None:
        hub.notify(force=True)
        _persist_serve()

    hub.attach(
        orch,
        pending_provider=lambda: list(pending),
        app_label="HandForge serve",
    )
    controller.attach(
        orch,
        settings,
        pending=pending,
        preset_name="MP3 192k",
        notify=_serve_notify,
    )

    def on_started(wid: int, file_path: str) -> None:
        hub.on_started(wid, file_path)
        _persist_serve()

    def on_progress(
        wid: int,
        progress: float,
        elapsed: float,
        eta: float,
        speed: str,
        *_rest,
    ) -> None:
        hub.on_progress(wid, progress, elapsed, eta, speed)

    def on_done(wid: int, success: bool, message: str, output_path: str) -> None:
        hub.on_done(wid, success, message, output_path)
        _persist_serve()

    orch.sig_worker_started.connect(on_started)
    orch.sig_worker_progress.connect(on_progress)
    orch.sig_worker_done.connect(on_done)
    _persist_serve()

    try:
        server = CompanionServer(
            hub, host=host, port=port, token=token, controller=controller
        )
        server.start()
    except (OSError, ValueError) as exc:
        print(f"Companion server failed: {exc}", file=sys.stderr)
        return EXIT_FAIL

    print(format_companion_status(settings))
    print(f"Shared workstation UI: {companion_url(host, port, token)}")
    print(
        "Control API (token required): POST /api/control/start|stop|jobs|options"
    )
    print(
        "Add absolute media paths on this host via the web UI, then Start. "
        "Anyone with the token can control this session — keep it private."
    )
    print("Press Ctrl+C to stop.")
    try:
        while True:
            app.processEvents()
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nStopping companion…", file=sys.stderr)
        orch.stop_all()
        _persist_serve()
    finally:
        server.stop()
        if not pending and not orch.job_queue and not orch.workers:
            clear_queue_state()
        else:
            _persist_serve()
        # Drain Qt events after stop
        if QCoreApplication.instance() is not None:
            app.processEvents()
    return EXIT_OK


def cmd_convert(args: argparse.Namespace) -> int:
    if not find_ffmpeg():
        print(
            format_actionable_error("FFmpeg not found on PATH"),
            file=sys.stderr,
        )
        return EXIT_FAIL

    settings = load_settings()
    if args.parallel is not None:
        settings["parallel"] = max(1, int(args.parallel))
    if args.no_adaptive:
        settings["adaptive_parallel"] = False
    if getattr(args, "hw_accel", None):
        settings["hw_accel"] = normalize_hw_preference(args.hw_accel)
    if getattr(args, "cloud_remote", None):
        settings["rclone_remote"] = str(args.cloud_remote).strip()
    if getattr(args, "no_rclone", False):
        settings["rclone_enabled"] = False
    if getattr(args, "analytics", False):
        settings["performance_analytics"] = True
    if getattr(args, "no_analytics", False):
        settings["performance_analytics"] = False
    if getattr(args, "companion", False):
        settings["companion_enabled"] = True
    if getattr(args, "companion_host", None):
        settings["companion_host"] = str(args.companion_host).strip()
    if getattr(args, "companion_port", None) is not None:
        settings["companion_port"] = int(args.companion_port)
    if getattr(args, "companion_token", None) is not None:
        settings["companion_token"] = str(args.companion_token)
    if getattr(args, "companion_lan", False):
        settings["companion_host"] = "0.0.0.0"

    staging_to_clean: List[str] = []
    try:
        prepared_in = prepare_inputs(args.inputs, settings=settings)
        staging_to_clean.extend(prepared_in.staging_dirs)
        try:
            inputs = collect_inputs(prepared_in.paths)
        except FileNotFoundError as exc:
            print(format_actionable_error(str(exc), exc=exc), file=sys.stderr)
            return EXIT_USAGE

        if not inputs:
            print("No supported media files found in the given paths.", file=sys.stderr)
            return EXIT_USAGE

        try:
            options = resolve_conversion_options(args)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return EXIT_USAGE

        out_spec = (
            args.cloud_output
            or args.output_dir
            or settings.get("output_dir")
            or _default_output_dir()
        )
        try:
            resolved_out = prepare_output(str(out_spec), settings=settings)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            print(format_actionable_error(str(exc), exc=exc), file=sys.stderr)
            return EXIT_FAIL
        if resolved_out.staging:
            staging_to_clean.append(resolved_out.local_dir)
        out_dir = resolved_out.local_dir

        try:
            probe = os.path.join(out_dir, f".handforge_cli_write_{os.getpid()}")
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write("ok")
            os.remove(probe)
        except OSError as exc:
            print(
                format_actionable_error(
                    f"Cannot write to output directory '{out_dir}': {exc}",
                    exc=exc,
                ),
                file=sys.stderr,
            )
            return EXIT_FAIL

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

        dest_label = resolved_out.rclone_dest or out_dir
        if not args.quiet:
            print(
                f"HandForge CLI {__version__}: {len(jobs)} job(s) → {dest_label} "
                f"(format={options.get('format')}, parallel={settings.get('parallel')})",
                file=sys.stderr,
                flush=True,
            )

        _ok, failed = run_batch(
            jobs,
            settings,
            quiet=args.quiet,
            verbose=args.verbose,
            companion=bool(getattr(args, "companion", False)),
            companion_host=getattr(args, "companion_host", None),
            companion_port=getattr(args, "companion_port", None),
            companion_token=getattr(args, "companion_token", None),
            companion_lan=bool(getattr(args, "companion_lan", False)),
        )
        if failed:
            print(f"Completed with {failed} failure(s).", file=sys.stderr)
            return EXIT_FAIL

        if resolved_out.rclone_dest:
            try:
                if not args.quiet:
                    print(
                        f"Uploading outputs to {resolved_out.rclone_dest} via rclone…",
                        file=sys.stderr,
                        flush=True,
                    )
                push_output(resolved_out, settings=settings)
            except (FileNotFoundError, RuntimeError, OSError) as exc:
                print(
                    format_actionable_error(
                        f"Conversion succeeded locally but rclone upload failed: {exc}",
                        exc=exc,
                    ),
                    file=sys.stderr,
                )
                return EXIT_FAIL

        if not args.quiet:
            print(f"Completed {len(jobs)} conversion(s) successfully.", file=sys.stderr)
        return EXIT_OK
    except FileNotFoundError as exc:
        print(format_actionable_error(str(exc), exc=exc), file=sys.stderr)
        return EXIT_FAIL
    except RuntimeError as exc:
        print(format_actionable_error(str(exc), exc=exc), file=sys.stderr)
        return EXIT_FAIL
    finally:
        cleanup_staging(staging_to_clean)


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

    p_hw = sub.add_parser(
        "list-hw-accel",
        help="Detect FFmpeg hardware video encoders (NVENC, Quick Sync, VAAPI, VideoToolbox)",
    )
    p_hw.add_argument(
        "--no-probe",
        action="store_true",
        help="Only list encoders compiled into FFmpeg (skip live encode probe)",
    )
    p_hw.set_defaults(func=cmd_list_hw_accel)

    p_plugins = sub.add_parser(
        "list-plugins",
        help="List discovered HandForge plugins (directory + entry points)",
    )
    p_plugins.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show registered presets and hook counts",
    )
    p_plugins.set_defaults(func=cmd_list_plugins)

    p_cloud = sub.add_parser(
        "list-cloud",
        help=(
            "Show rclone availability/remotes and local cloud sync roots "
            "(Dropbox / Google Drive / OneDrive / Nextcloud / configured)"
        ),
    )
    p_cloud.set_defaults(func=cmd_list_cloud)

    p_analytics = sub.add_parser(
        "list-analytics",
        help=(
            "Show local performance-analytics status and recent batch summaries "
            "(~/.handforge/analytics/; never uploaded)"
        ),
    )
    p_analytics.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of recent batches to show (default: 5)",
    )
    p_analytics.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Include per-job lines in each summary",
    )
    p_analytics.add_argument(
        "--report",
        action="store_true",
        help=(
            "Print advanced aggregate analytics report "
            "(success rate, mean/peak speed, throughput, ETA MAE)"
        ),
    )
    p_analytics.set_defaults(func=cmd_list_analytics)

    p_watch = sub.add_parser(
        "watch",
        help=(
            "Watch-folder / hotfolder: poll directories for new media and convert "
            "(tracks seen files in ~/.handforge/seen_files.json)"
        ),
    )
    p_watch.add_argument(
        "folders",
        nargs="*",
        help="Directories to watch (default: settings watchfolder_dirs)",
    )
    p_watch.add_argument(
        "--dir",
        action="append",
        dest="dir",
        help="Additional watch directory (repeatable)",
    )
    p_watch.add_argument(
        "-o",
        "--output-dir",
        help="Output directory for conversions",
    )
    p_watch.add_argument("--preset", help="Preset name or template id")
    p_watch.add_argument("-f", "--format", help="Output format (e.g. mp3, flac, mp4)")
    p_watch.add_argument("--mode", help="CBR / VBR / Lossless")
    p_watch.add_argument("--bitrate", type=int, help="Audio bitrate kbps")
    p_watch.add_argument("--vbrq", type=int, help="VBR quality")
    p_watch.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Poll interval seconds (default: settings or 5)",
    )
    p_watch.add_argument(
        "--settle",
        type=float,
        default=1.5,
        help="Seconds a new file must stay size-stable before convert (default: 1.5)",
    )
    p_watch.add_argument(
        "--once",
        action="store_true",
        help="Scan twice (seed + settle) then exit instead of looping",
    )
    p_watch.add_argument(
        "--no-recursive",
        action="store_true",
        help="Only watch the top of each folder (no subdirectories)",
    )
    p_watch.add_argument("--parallel", type=int, help="Max parallel conversions")
    p_watch.add_argument(
        "--no-adaptive",
        action="store_true",
        help="Disable adaptive parallel scheduling",
    )
    p_watch.add_argument(
        "--analytics",
        action="store_true",
        help="Enable local performance analytics for conversions",
    )
    p_watch.add_argument(
        "--no-analytics",
        action="store_true",
        help="Disable analytics for this run",
    )
    p_watch.add_argument("-q", "--quiet", action="store_true")
    p_watch.add_argument("-v", "--verbose", action="store_true")
    p_watch.set_defaults(func=cmd_watch)

    p_serve = sub.add_parser(
        "serve",
        help=(
            "Start the companion remote queue-monitor HTTP server "
            "(mobile web UI + /api/status; opt-in; default localhost)"
        ),
    )
    p_serve.add_argument(
        "--host",
        default=None,
        help="Bind address (default: settings or 127.0.0.1)",
    )
    p_serve.add_argument(
        "--port",
        type=int,
        default=None,
        help="TCP port (default: settings or 8765)",
    )
    p_serve.add_argument(
        "--token",
        default=None,
        help="Shared token (required for non-localhost; query ?token=…)",
    )
    p_serve.add_argument(
        "--lan",
        action="store_true",
        help="Bind 0.0.0.0 for phone-on-LAN access (auto-mints token if unset)",
    )
    p_serve.set_defaults(func=cmd_serve)

    p_conv = sub.add_parser(
        "convert",
        help="Convert one or more media files or directories",
    )
    p_conv.add_argument(
        "inputs",
        nargs="+",
        help=(
            "Input file(s) and/or directories (directories are scanned recursively). "
            "rclone paths use remote:path (requires rclone on PATH)"
        ),
    )
    p_conv.add_argument(
        "-o",
        "--output-dir",
        help=(
            "Output directory (default: settings or ~/HandForge_Output). "
            "May be a local sync folder or rclone remote:path"
        ),
    )
    p_conv.add_argument(
        "--cloud-remote",
        help="Default rclone remote name (e.g. gdrive); stored for this run only",
    )
    p_conv.add_argument(
        "--cloud-output",
        help="rclone remote:path for outputs (stages locally, then rclone copy)",
    )
    p_conv.add_argument(
        "--no-rclone",
        action="store_true",
        help="Disable rclone remote:path handling for this run",
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
        "--hw-accel",
        choices=list(HW_PREFERENCES),
        help=(
            "Hardware video encoder preference "
            "(auto|software|nvenc|qsv|vaapi|videotoolbox); "
            "falls back to software if unavailable or encode fails"
        ),
    )
    p_conv.add_argument(
        "--extract-audio",
        action="store_true",
        help="Extract audio only from video sources",
    )
    p_conv.add_argument(
        "--eq",
        action="store_true",
        help="Enable 3-band EQ (use with --eq-bass/--eq-mid/--eq-treble)",
    )
    p_conv.add_argument(
        "--eq-bass",
        type=float,
        help="EQ bass gain in dB (~100 Hz); enables EQ",
    )
    p_conv.add_argument(
        "--eq-mid",
        type=float,
        help="EQ mid gain in dB (~1 kHz); enables EQ",
    )
    p_conv.add_argument(
        "--eq-treble",
        type=float,
        help="EQ treble gain in dB (~8 kHz); enables EQ",
    )
    p_conv.add_argument(
        "--compressor",
        action="store_true",
        help="Enable acompressor (settings defaults or --compressor-*)",
    )
    p_conv.add_argument(
        "--compressor-threshold",
        type=float,
        help="Compressor threshold (linear 0–1); enables compressor",
    )
    p_conv.add_argument(
        "--compressor-ratio",
        type=float,
        help="Compressor ratio; enables compressor",
    )
    p_conv.add_argument(
        "--limiter",
        action="store_true",
        help="Enable alimiter peak limiting",
    )
    p_conv.add_argument(
        "--limiter-limit",
        type=float,
        help="Limiter ceiling (linear 0–1); enables limiter",
    )
    p_conv.add_argument(
        "--denoise",
        action="store_true",
        help="Enable afftdn FFT noise reduction",
    )
    p_conv.add_argument(
        "--denoise-nr",
        type=float,
        help="Denoise reduction in dB; enables denoise",
    )
    p_conv.add_argument(
        "--denoise-nf",
        type=float,
        help="Denoise noise floor in dB; enables denoise",
    )
    p_conv.add_argument(
        "--video-color",
        action="store_true",
        help="Enable video color adjust (eq brightness/contrast/saturation)",
    )
    p_conv.add_argument(
        "--brightness",
        type=float,
        help="Video brightness (−1.0…1.0); enables color adjust",
    )
    p_conv.add_argument(
        "--contrast",
        type=float,
        help="Video contrast (typically 0…2); enables color adjust",
    )
    p_conv.add_argument(
        "--saturation",
        type=float,
        help="Video saturation (0…3); enables color adjust",
    )
    p_conv.add_argument(
        "--stabilize",
        action="store_true",
        help="Enable single-pass video stabilization (deshake)",
    )
    p_conv.add_argument(
        "--stabilize-rx",
        type=int,
        help="Stabilization horizontal search range 0–64; enables stabilize",
    )
    p_conv.add_argument(
        "--stabilize-ry",
        type=int,
        help="Stabilization vertical search range 0–64; enables stabilize",
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
        "--analytics",
        action="store_true",
        help=(
            "Enable local performance analytics for this run "
            "(speed, duration, throughput, peak parallel, ETA accuracy; "
            "stored under ~/.handforge/analytics/)"
        ),
    )
    p_conv.add_argument(
        "--no-analytics",
        action="store_true",
        help="Disable performance analytics for this run (overrides settings)",
    )
    p_conv.add_argument(
        "--companion",
        action="store_true",
        help=(
            "Expose companion remote queue monitor during this convert "
            "(HTTP + mobile web UI; see also `handforge serve`)"
        ),
    )
    p_conv.add_argument(
        "--companion-host",
        help="Companion bind host (default: settings or 127.0.0.1)",
    )
    p_conv.add_argument(
        "--companion-port",
        type=int,
        help="Companion TCP port (default: settings or 8765)",
    )
    p_conv.add_argument(
        "--companion-token",
        help="Companion shared token (required for LAN bind)",
    )
    p_conv.add_argument(
        "--companion-lan",
        action="store_true",
        help="Bind companion on 0.0.0.0 for phone-on-LAN (auto-mints token if unset)",
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
    from .plugins import ensure_plugins_loaded

    ensure_plugins_loaded(load_settings())
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
