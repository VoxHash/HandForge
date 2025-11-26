# Frequently Asked Questions

Common questions about HandForge.

## General

### What is HandForge?

HandForge is a cross-platform audio and video converter GUI built with PyQt6 and FFmpeg. It provides a user-friendly interface for batch audio/video conversion with presets, metadata management, progress tracking, and multi-language support.

### What platforms does HandForge support?

HandForge runs on:
- Windows 10+
- Linux (most distributions)
- macOS 10.14+

### Is HandForge free?

Yes, HandForge is open source and free to use under the MIT License.

## Installation

### Do I need FFmpeg?

Yes, FFmpeg is required. HandForge uses FFmpeg for all audio processing.

### How do I install FFmpeg?

- **Windows**: `winget install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org)
- **Linux**: `sudo apt install ffmpeg` (Ubuntu/Debian)
- **macOS**: `brew install ffmpeg`

### What Python version do I need?

Python 3.9 or higher is required.

## Usage

### How do I convert files?

1. Add files to the queue
2. Select a preset
3. Click "Start"

See [Usage Guide](usage.md) for details.

### What formats are supported?

HandForge supports all formats that FFmpeg can read, including:
- Lossy: mp3, aac, m4a, ogg, wma, opus
- Lossless: flac, wav, aiff, alac, ape, wavpack

### Where are converted files saved?

By default, files are saved to `~/HandForge_Output` (or `%USERPROFILE%\HandForge_Output` on Windows).

### Can I change the output folder?

Yes! You can change the output directory in **Settings** → **Preferences** → **Conversion** tab.

### How do I create custom presets?

Go to **Settings** → **Manage Presets** → Create new preset.

### Can I convert multiple files at once?

Yes! Add multiple files to the queue and they'll be processed in parallel (configurable).

## Features

### Does HandForge preserve metadata?

Yes, HandForge preserves metadata when possible. You can also edit metadata per file.

### Can I add cover art?

Yes, you can:
- Use external cover art (folder.jpg, cover.jpg)
- Add cover art via metadata editor
- Preserve embedded cover art

### What is auto-retry?

Auto-retry automatically retries failed conversions when specific error patterns are detected.

### Can I pause conversions?

Yes, you can pause all conversions or individual workers.

### Does HandForge support batch processing?

Yes, add multiple files or folders to process them all at once.

## Troubleshooting

### Conversions are failing. What should I do?

1. Check FFmpeg is installed correctly
2. Verify input files are valid
3. Check error logs (click "🔎 log" on failed items)
4. Try "Retry Failed (Safe)" with WAV format
5. See [Troubleshooting Guide](troubleshooting.md)

### HandForge is slow. How can I speed it up?

1. Increase parallel count (if system allows)
2. Close other applications
3. Check system resources
4. Process smaller batches

### Files aren't being added to the queue. Why?

1. Check Media Filter setting
2. Verify file format is supported
3. Files may already be in queue (duplicates are skipped)
4. Check file permissions

## Technical

### Can I use HandForge from the command line?

CLI support is planned for a future release. Currently, HandForge is GUI-only.

### Can I integrate HandForge into my application?

HandForge modules can be imported, but it's designed primarily as a GUI application. See [API Reference](api.md) for details.

### How does HandForge handle threading?

HandForge uses Qt's threading model with worker threads for FFmpeg processes and signals for thread-safe communication.

### Where are settings stored?

Settings are stored in `~/.handforge/` (or `%USERPROFILE%\.handforge\` on Windows) as JSON files.

## Support

### Where can I get help?

- [Documentation](index.md)
- [Troubleshooting Guide](troubleshooting.md)
- [GitHub Issues](https://github.com/VoxHash/HandForge/issues)
- Email: contact@voxhash.dev

### How do I report a bug?

Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md) on GitHub Issues.

### How do I suggest a feature?

Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md) on GitHub Issues.

### Can I contribute?

Yes! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

---

**More questions?** See [Support](../SUPPORT.md).

