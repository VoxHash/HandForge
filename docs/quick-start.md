# Quick Start Guide

Get HandForge up and running in minutes!

## Installation

```bash
# Project venv (recommended)
python3 -m venv .venv && source .venv/bin/activate   # Windows: python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .

# Ensure FFmpeg is installed
# Windows: winget install ffmpeg
# Linux: sudo apt install ffmpeg
# macOS: brew install ffmpeg
```

Full desktop walkthrough (all OSes + post-install use): [desktop.md](desktop.md).

## Run

```bash
python -m handforge.app
# or: handforge convert input.mp3 --preset "MP3 192k" -o ./output
```

## Convert Your First File

1. Click **"Add Files"** or drag files into the window
2. Select a **preset** (e.g., "MP3 192k" for audio, "MP4 H.264" for video)
3. For video files with subtitles, select subtitle track in the queue table
4. Click **"Start Conversion"**
5. Monitor progress in the Active Conversions table
6. Find your converted files - location shown in status bar when complete

That's it! You're ready to convert audio and video files.

## What's Next?

- [Getting Started Guide](getting-started.md) - More detailed instructions
- [Usage Guide](usage.md) - Learn all features
- [Examples](examples/) - See HandForge in action

---

**Need help?** Check [Troubleshooting](troubleshooting.md) or [FAQ](faq.md).

