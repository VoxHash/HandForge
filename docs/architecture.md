# Architecture

This document describes the architecture and design of HandForge.

## Overview

HandForge is a cross-platform audio and video converter built with:

- **PyQt6** - GUI framework
- **FFmpeg** - Audio/video processing backend
- **Python 3.9+** - Programming language
- **Rust (optional)** - Adaptive parallel-job scheduler (`native/handforge_scheduler`)

## Architecture Layers

```
┌─────────────────────────────────────┐
│         UI Layer (PyQt6)            │
│  (MainWindow, Dialogs, Widgets)     │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│      Core Layer                     │
│  (Orchestrator, Models, Settings,   │
│   native_scheduler)                 │
└─────────────────────────────────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌──────────┐  ┌──────────────────────┐
│ Utility  │  │ Native (optional)    │
│ (FFmpeg) │  │ Rust cdylib via      │
│          │  │ ctypes               │
└──────────┘  └──────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│      External (FFmpeg)              │
└─────────────────────────────────────┘
```

## Core Components

### MainWindow (`ui/main_window.py`)

The main application window that provides:

- File queue management
- Workers table for progress tracking
- Menu system
- Settings dialogs
- Event handling

### Orchestrator (`core/orchestrator.py`)

Manages the conversion process:

- Worker thread pool
- Job queue
- Parallel execution control (user ceiling + adaptive limit)
- Signal-based communication

### Native scheduler (`core/native_scheduler.py` + `native/handforge_scheduler`)

Optional Rust `cdylib` that recommends concurrent job slots from available memory and load average. Python loads it with `ctypes` when present; otherwise the same heuristics run in pure Python. FFmpeg workers stay in Python/QThread — only the scheduling hot path is native.

### Progress tracking (`core/progress.py`)

Per-worker `ProgressTracker` keeps percent monotonic, computes wall-clock ETA from FFmpeg `speed=`, applies Preferences `ewma_alpha`, and throttles signal emits so many parallel jobs do not flood the Qt event loop. The main window coalesces Active Conversions table redraws (~150 ms) and shows aggregate batch progress in the status bar.

### Worker (`core/orchestrator.py`)

Individual conversion worker:

- Runs in QThread
- Executes FFmpeg process
- Parses progress output
- Emits progress signals

### Models (`core/models.py`)

Data structures:

- `Job` - Represents a conversion job

### Settings (`core/settings.py`)

Configuration management:

- JSON-based storage
- Settings, presets, patterns
- Auto-retry rules
- File cache

### FFmpeg Utilities (`util/ffmpeg.py`)

FFmpeg integration:

- Command building
- Process execution
- Path utilities
- Cover art handling

### Hardware acceleration (`util/hwaccel.py`)

Probes `ffmpeg -encoders` and runs a short lavfi encode to verify NVENC, Quick Sync, VAAPI, and VideoToolbox. `resolve_hw_encode()` maps Preferences / CLI `hw_accel` (`auto` / `software` / backend) onto a concrete encoder plus any pre-`-i` device args (VAAPI/QSV). `build_ffmpeg_cmd(..., hw_accel=...)` applies the plan; orchestrator workers retry once with software (`libx264` / `libx265`) if a HW encode fails.

### Advanced audio filters (`util/audio_filters.py`)

`build_audio_filter_graph()` assembles real FFmpeg filters: `afftdn` (denoise), `equalizer` (3-band EQ), `acompressor`, `alimiter`, plus existing fade / `loudnorm`. `build_ffmpeg_cmd` applies the joined `-af` chain for audio and video jobs when any filter is enabled. Defaults are all off.

### Video filters (`util/video_filters.py`)

`build_video_filter_graph()` assembles real FFmpeg filters: `deshake` (single-pass stabilization) and `eq` (brightness / contrast / saturation). `build_ffmpeg_cmd` inserts them into the software `-vf` chain before scale and HW upload (`format` / `hwupload`), so color/stabilize work with both software and HW encoders. Multi-pass `vidstabdetect`/`vidstabtransform` is not used (needs a separate analysis pass); `deshake` is the practical single-pass default. Defaults are all off.

### Plugins (`plugins/`)

Lightweight extensibility without forking:

- **Discovery** — `~/.handforge/plugins/<name>/plugin.py`, `HANDFORGE_PLUGIN_DIRS` / settings `plugin_dirs`, and packaging entry points (`handforge.plugins`)
- **Presets** — `register_preset()` merges into `all_presets()` (custom presets still win on name clash)
- **Hooks** — `register_pre_convert` / `register_post_convert` run inside Orchestrator workers around each encode; failures are logged only

See [plugins.md](plugins.md) and the in-repo example under `examples/plugins/archive_flac_sidecar/`.

## Data Flow

```
User Action
    │
    ▼
MainWindow
    │
    ▼
Creates Jobs
    │
    ▼
Orchestrator.enqueue()
    │
    ▼
Worker Threads
    │
    ▼
FFmpeg Process
    │
    ▼
Progress Signals
    │
    ▼
UI Update
```

## Threading Model

HandForge uses Qt's threading model:

- **Main Thread**: UI updates and event handling
- **Worker Threads**: FFmpeg process execution
- **Signal/Slot**: Thread-safe communication

## Configuration Storage

Settings are stored in JSON files:

- Location: `~/.handforge/`
- Files:
  - `settings.json` - Application settings
  - `presets.json` - Conversion presets
  - `patterns.json` - Filename patterns
  - `autoretry.json` - Auto-retry rules
  - `seen_files.json` - Processed files cache

## Error Handling

- FFmpeg errors are captured in stderr
- Worker signals indicate success/failure
- Auto-retry system handles transient errors
- Logs are stored for debugging

## Extension Points

Future extensibility:

- Plugin system for custom codecs
- Custom metadata handlers
- Output format plugins
- Custom UI themes

## Performance Considerations

- Parallel processing for multiple files
- Thread pool management
- Memory-efficient file processing
- Progress tracking without blocking

## Dependencies

- **PyQt6**: GUI framework
- **FFmpeg**: Audio processing (external)
- **Python stdlib**: File operations, JSON, subprocess

## Design Principles

1. **Separation of Concerns**: UI, business logic, and utilities are separated
2. **Signal-Based Communication**: Qt signals for thread-safe communication
3. **Modularity**: Each component has a clear responsibility
4. **Extensibility**: Easy to add new features
5. **User Experience**: Responsive UI with real-time feedback

---

**For development**, see [Contributing](../CONTRIBUTING.md).

