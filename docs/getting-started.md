# Getting Started with HandForge

From a fresh machine to your first conversion. For the full cross-platform install + day-to-day GUI/CLI checklist, see [Desktop install & usage](desktop.md).

## Prerequisites

- **Python 3.9+**
- **FFmpeg** on PATH (`ffmpeg -version`)
- **pip** / **venv**

## Installation (canonical project `.venv`)

```bash
git clone https://github.com/VoxHash/HandForge.git
cd HandForge

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows PowerShell:
#   python -m venv .venv
#   .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

FFmpeg (if missing):

```bash
# Windows: winget install ffmpeg
# Linux (Debian/Ubuntu): sudo apt install ffmpeg
# macOS: brew install ffmpeg
```

Verify:

```bash
python -c "import PyQt6; import handforge; print('HandForge OK')"
handforge --version
ffmpeg -version
```

Platform detail: [installation.md](installation.md) · end-to-end: [desktop.md](desktop.md).

## Running HandForge

### GUI

```bash
python -m handforge.app
```

### CLI (no display)

```bash
handforge convert input.mp3 --preset "MP3 192k" -o ./output
handforge list-presets
handforge list-templates --category Podcast -v
```

## Your First Conversion (GUI)

1. **Add Files** or drag-and-drop into the queue
2. Select a **preset** (e.g. "MP3 192k" or a video preset)
3. For video with subtitles, pick the subtitle track in the queue table if needed
4. **Start Conversion** (Ctrl+Return)
5. Watch **Active Conversions**; find output under `~/HandForge_Output` by default (`%USERPROFILE%\HandForge_Output` on Windows)

## Next Steps

- [Desktop install & usage](desktop.md)
- [Usage Guide](usage.md)
- [CLI](cli.md)
- [Configuration](configuration.md)
- [Examples](examples/)
- [Troubleshooting](troubleshooting.md)

## Getting Help

- [FAQ](faq.md)
- [Support](../SUPPORT.md) — contact@voxhash.dev

---

© 2026 VoxHash Technologies
