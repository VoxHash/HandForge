# API Reference

HandForge is primarily a GUI application, but the core modules can be imported and used programmatically.

## Core Modules

### handforge.core.settings

Application settings management.

```python
from handforge.core import settings

# Load settings
config = settings.load_settings()

# Save settings
settings.save_settings({"parallel": 4})

# Load presets
presets = settings.load_custom_presets()

# Save presets
settings.save_custom_presets({"My Preset": {...}})
```

### handforge.core.presets

Built-in presets, curated template library, and import/export.

```python
from handforge.core.presets import (
    list_templates,
    get_template,
    get_preset,
    apply_template,
    export_presets,
    import_presets,
)

# Browse curated templates (Apple Podcasts / YouTube-aligned, etc.)
for t in list_templates(category="Podcast"):
    print(t["id"], t["name"], t["options"])

# Resolve built-in, custom, or template by id/name
opts = get_preset("podcast-aac-128")

# Install a template into ~/.handforge/presets.json
name, opts = apply_template("youtube-1080p-h264", as_name="YT 1080p")

export_presets("backup.json")
import_presets("backup.json", replace=False)
```

### handforge.core.models

Data models.

```python
from handforge.core.models import Job

# Create a job
job = Job(
    src="/path/to/input.mp3",
    dst_dir="/path/to/output",
    format="mp3",
    mode="CBR",
    bitrate="192",
    meta_title="Song Title",
    meta_artist="Artist Name"
)
```

### handforge.core.orchestrator

Conversion orchestrator.

```python
from handforge.core.orchestrator import Orchestrator
from handforge.core.models import Job

# Create orchestrator
orch = Orchestrator(threads_per_job=1, max_parallel=2)

# Connect signals
orch.sig_worker_done.connect(lambda wid, ok, msg: print(f"Done: {ok}"))

# Enqueue jobs
jobs = [Job(...), Job(...)]
orch.enqueue(jobs)
```

### handforge.util.errors

Actionable conversion error mapping (shared by orchestrator, CLI, and GUI).

```python
from handforge.util.errors import classify_error, format_actionable_error

err = classify_error("Unknown encoder 'libx265'")
print(err.code, err.title)          # unsupported_encoder / Encoder / codec unavailable
print(err.format())                 # summary + "What to try:" steps

print(format_actionable_error("No space left on device"))
```

### handforge.util.ffmpeg

FFmpeg utilities.

```python
from handforge.util.ffmpeg import build_ffmpeg_cmd, run_ffmpeg, out_path

# Build FFmpeg command
cmd = build_ffmpeg_cmd(
    src="input.mp3",
    dst="output.m4a",
    fmt="m4a",
    mode="CBR",
    bitrate="256",
    metadata={"title": "Song", "artist": "Artist"}
)

# Run FFmpeg
proc = run_ffmpeg(cmd)

# Generate output path
output = out_path("/output", "input.mp3", "mp3")

# Video with hardware acceleration preference
cmd = build_ffmpeg_cmd(
    src="input.mkv",
    dst="output.mp4",
    fmt="mp4",
    hw_accel="auto",  # or software | nvenc | qsv | vaapi | videotoolbox
)

# Advanced audio filters (also accepted by build_ffmpeg_cmd)
cmd = build_ffmpeg_cmd(
    src="podcast.wav",
    dst="podcast.mp3",
    fmt="mp3",
    bitrate="192",
    eq_enabled=True,
    eq_bass=2.0,
    compressor_enabled=True,
    limiter_enabled=True,
    denoise_enabled=True,
)
```

### handforge.util.audio_filters

Build ordered FFmpeg `-af` fragments (denoise → EQ → compressor → limiter → fade → loudnorm).

```python
from handforge.util.audio_filters import (
    build_audio_filter_graph,
    join_audio_filters,
)

parts = build_audio_filter_graph(
    eq_enabled=True,
    eq_mid=1.5,
    compressor_enabled=True,
    limiter_enabled=True,
    denoise_enabled=True,
)
af = join_audio_filters(parts)  # ready for -af
```

### handforge.util.hwaccel

Hardware encoder detection and selection.

```python
from handforge.util.hwaccel import (
    detect_available_backends,
    format_detection_report,
    resolve_hw_encode,
)

info = detect_available_backends(probe=True)
print(format_detection_report(info))

plan = resolve_hw_encode("auto", software_codec="libx264", detection=info)
print(plan.backend, plan.encoder, plan.used_hw)
```

## Example: Programmatic Usage

```python
from handforge.core.models import Job
from handforge.core.orchestrator import Orchestrator
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
import sys

app = QtWidgets.QApplication(sys.argv)

# Create orchestrator
orch = Orchestrator(max_parallel=2)

# Handle completion
def on_done(wid, ok, msg):
    print(f"Worker {wid}: {'OK' if ok else 'FAILED'}")

orch.sig_worker_done.connect(on_done)

# Create jobs
jobs = [
    Job(
        src="input1.mp3",
        dst_dir="~/HandForge_Output",
        format="m4a",
        mode="CBR",
        bitrate="256"
    ),
    Job(
        src="input2.flac",
        dst_dir="~/HandForge_Output",
        format="mp3",
        mode="VBR",
        vbrq="2"
    )
]

# Start conversion
orch.enqueue(jobs)

# Keep app running
sys.exit(app.exec_())
```

## Module Structure

```
handforge/
├── core/
│   ├── models.py          # Data models (Job)
│   ├── orchestrator.py    # Conversion orchestrator
│   └── settings.py        # Settings management
├── dialogs/
│   ├── auto_retry.py      # Auto-retry dialog
│   ├── metadata.py        # Metadata editor
│   ├── patternmanagerdialog.py  # Pattern manager
│   └── presetsdialog.py   # Presets manager
├── ui/
│   └── main_window.py     # Main application window
└── util/
    ├── audio_filters.py   # EQ / compressor / limiter / denoise graphs
    ├── errors.py          # Actionable error classification / formatting
    ├── ffmpeg.py          # FFmpeg command builder
    └── hwaccel.py         # HW encoder probe / selection
```

## Notes

- HandForge is designed primarily as a GUI application
- Programmatic usage is possible but not the main use case
- The GUI provides the best user experience
- For headless batch scripting, use `python -m handforge` / the `handforge` CLI (see [CLI](cli.md))

---

**For GUI usage**, see [Usage Guide](usage.md).

