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
    └── ffmpeg.py          # FFmpeg utilities
```

## Notes

- HandForge is designed primarily as a GUI application
- Programmatic usage is possible but not the main use case
- The GUI provides the best user experience
- For batch scripting, consider using FFmpeg directly or wait for CLI support

---

**For GUI usage**, see [Usage Guide](usage.md).

