# HandForge

[![CodeQL Analysis](https://github.com/VoxHash/HandForge/actions/workflows/codeql.yml/badge.svg)](https://github.com/VoxHash/HandForge/actions/workflows/codeql.yml)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)]()

A cross-platform audio and video converter GUI (Windows/Linux) built with PyQt6 + FFmpeg. Features a modern Glassmorphism UI design.

## Features

- **Batch Queue**: Add many files, convert all at once
- **Audio & Video Support**: Convert between nearly any audio and video formats FFmpeg supports
  - **Audio**: mp3, m4a/aac, opus, ogg/vorbis, flac, alac, wav, aiff, wma, ac3/eac3, ape, tta, wavpack, mp2, amr, caf, au, mka and more
  - **Video**: mp4, mkv, avi, mov, wmv, flv, webm, m4v, 3gp, ogv, mts, m2ts, ts, and more
- **Video to Audio Extraction**: Extract audio tracks from video files
- **Video Conversion**: Convert videos between different formats with customizable codecs, bitrates, resolution, and FPS
- **Subtitle Selection**: Per-file subtitle track selection for video conversions (MKV multi-subtitle to MP4 single-subtitle)
- **Smart Video Compression**: Reduce video file size by 5-10x while maintaining quality using H.265/HEVC codec
- **Two-Pass Encoding**: Optional two-pass encoding for optimal quality/size ratio
- **Encoding Modes**: CBR / VBR / Lossless modes for audio
- **Customizable**: Choose bitrate, sample rate, channels, video codec, resolution, FPS
- **EBU R128 Loudness Normalization**: Built-in `loudnorm` filter support
- **Presets**: Save and load custom conversion presets (audio and video)
- **Metadata Management**: Copy or strip metadata, per-file overrides
- **Cover Art**: Prefer external cover toggle; preserve embedded cover when available
- **Parallel Processing**: Parallel encodes with per-codec thread caps
- **Workers Table**: Real-time progress tracking with elapsed/ETA/speed, status colors, inline log viewer, progress bars with ETA
- **Queue Management**: Files remain in queue until processing starts, accurate queue counter
- **Auto-Retry**: Configurable auto-retry rules (JSON import/export)
- **Resume Support**: Resume pending items from last session
- **Glassmorphism UI**: Modern transparent glass-like interface with blur effects
- **Export/Import**: Export/import presets & patterns (CSV/JSON)
- **Drag & Drop**: Easy file management with drag & drop support
- **Output Folder Selection**: Customizable output directory
- **Preferences Dialog**: Comprehensive settings management with tabbed interface
- **Audio Trimming & Effects**: Trim audio files and apply fade in/out effects
- **Video Editing**: Trim, crop, scale resolution, and convert frame rates
- **Video Quality Presets**: Low, medium, high, ultra quality options
- **Multiple Audio Tracks**: Select specific audio tracks from multi-track videos
- **Audio Quality Analysis**: Analyze audio quality metrics
- **System Tray**: Minimize to tray with conversion notifications
- **Multi-Language Support (i18n)**: Full internationalization with 11 languages (English, Russian, Portuguese, Spanish, Estonian, French, German, Japanese, Chinese, Korean, Indonesian)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure FFmpeg is installed and on PATH
# Windows: winget install ffmpeg
# Linux: sudo apt install ffmpeg

# Run the application
python -m handforge.app
```

## Installation

See [docs/installation.md](docs/installation.md) for detailed installation instructions.

## Usage

See [docs/usage.md](docs/usage.md) for detailed usage instructions.

## Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `parallel` | Number of parallel encodes | 2 |
| `dark_theme` | Enable dark theme | false |
| `prefer_external_cover` | Prefer external cover art | false |
| `dup_handling` | Duplicate file handling | Overwrite |
| `on_exists` | Behavior when output exists | overwrite |
| `normalize_lufs` | Enable loudness normalization | false |
| `target_lufs` | Target LUFS value | -14.0 |
| `delete_original` | Delete original file after conversion | false |
| `minimize_to_tray` | Minimize to system tray on close | true |
| `output_dir` | Default output directory | ~/HandForge_Output |
| `default_video_quality` | Default video quality preset | medium |
| `default_video_codec` | Default video codec | libx264 |
| `default_reduction_factor` | Default size reduction factor | 7.0 |
| `default_two_pass` | Enable two-pass encoding by default | false |
| `language` | Interface language (None = auto-detect) | None |

See [docs/configuration.md](docs/configuration.md) for complete configuration options.

## Examples

See [docs/examples/](docs/examples/) for usage examples.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features and improvements.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please see [SUPPORT.md](SUPPORT.md) or contact contact@voxhash.dev.

## Security

For security concerns, please see [SECURITY.md](SECURITY.md).

---

**HandForge** - Audio conversion made simple  
© 2025 VoxHash Technologies
