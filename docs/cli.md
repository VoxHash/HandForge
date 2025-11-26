# Command-Line Interface

> **Note**: CLI support is planned for a future release. Currently, HandForge is GUI-only.

## Planned CLI Features

The command-line interface will support:

- Batch conversion from command line
- Preset-based conversions
- Scriptable workflows
- Integration with other tools

## Current Workaround

Until CLI is available, you can use FFmpeg directly for command-line conversions:

```bash
# Convert MP3 to AAC
ffmpeg -i input.mp3 -c:a aac -b:a 192k output.m4a

# Convert with metadata
ffmpeg -i input.mp3 -c:a libmp3lame -b:a 192k \
  -metadata title="Song Title" \
  -metadata artist="Artist Name" \
  output.mp3
```

## Future CLI Usage (Planned)

```bash
# Basic conversion
handforge convert input.mp3 --preset "MP3 192k"

# Batch conversion
handforge convert *.mp3 --preset "AAC 256k" --output-dir ./output

# With metadata
handforge convert input.mp3 --preset "MP3 192k" \
  --title "Song Title" \
  --artist "Artist Name"

# List presets
handforge list-presets

# Create preset
handforge create-preset "My Preset" --format mp3 --mode CBR --bitrate 192
```

## Stay Updated

Check the [Roadmap](../ROADMAP.md) for CLI development progress.

---

**For now**, use the GUI application: `python -m handforge.app`

