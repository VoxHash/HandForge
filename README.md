# HandForge

[![CodeQL Analysis](https://github.com/VoxHash/HandForge/actions/workflows/codeql.yml/badge.svg)](https://github.com/VoxHash/HandForge/actions/workflows/codeql.yml)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

> A cross-platform audio and video converter GUI (Windows/Linux/macOS) built with PyQt6 + FFmpeg. Features a modern Glassmorphism UI design.

## ✨ Features

- **Batch Queue**: Add many files, convert all at once
- **Audio & Video Support**: Convert between nearly any audio and video formats FFmpeg supports
- **Smart Video Compression**: Reduce video file size by 5-10x while maintaining quality using H.265/HEVC
- **Two-Pass Encoding**: Optional two-pass encoding for optimal quality/size ratio
- **Parallel Processing**: Parallel encodes with per-codec thread caps
- **Presets System**: Save and load custom conversion presets (audio and video)
- **Metadata Management**: Copy or strip metadata, per-file overrides
- **Multi-Language Support**: Full internationalization with 11 languages
- **System Tray**: Minimize to tray with conversion notifications
- **Real-time Progress**: Progress tracking with elapsed/ETA/speed and visual progress bars

## 🧭 Table of Contents

- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage](#-usage)
- [Configuration](#-configuration)
- [Examples](#-examples)
- [Architecture](#-architecture)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Quick Start

```bash
# 1) Install dependencies
pip install -r requirements.txt

# 2) Ensure FFmpeg is installed and on PATH
# Windows: winget install ffmpeg
# Linux: sudo apt install ffmpeg

# 3) Run the application
python -m handforge.app
```

## 💿 Installation

See [docs/installation.md](docs/installation.md) for platform-specific installation instructions.

## 🛠 Usage

Basic usage: Add files to the queue, select a preset, and start conversion. Advanced usage in [docs/usage.md](docs/usage.md).

### Supported Formats

**Audio**: mp3, m4a/aac, opus, ogg/vorbis, flac, alac, wav, aiff, wma, ac3/eac3, ape, tta, wavpack, mp2, amr, caf, au, mka and more

**Video**: mp4, mkv, avi, mov, wmv, flv, webm, m4v, 3gp, ogv, mts, m2ts, ts, and more

## ⚙️ Configuration

Key settings (full reference: [docs/configuration.md](docs/configuration.md)):

| Setting | Description | Default |
|---------|-------------|---------|
| `parallel` | Number of parallel encodes | 2 |
| `output_dir` | Default output directory | ~/HandForge_Output |
| `default_video_quality` | Default video quality preset | medium |
| `default_video_codec` | Default video codec | libx264 |
| `language` | Interface language (None = auto-detect) | None |

## 📚 Examples

- Start here: [docs/examples/example-01.md](docs/examples/example-01.md)
- More examples: [docs/examples/](docs/examples/)

## 🧩 Architecture

High-level overview: HandForge uses a modular architecture with UI (PyQt6), core (orchestrator, models, settings), and utility (FFmpeg integration) layers. See [docs/architecture.md](docs/architecture.md) for details.

## 🗺 Roadmap

Planned milestones live in [ROADMAP.md](ROADMAP.md). For changes, see [CHANGELOG.md](CHANGELOG.md).

## 🤝 Contributing

We welcome PRs! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and follow the PR template.

## 🔒 Security

Please report vulnerabilities via [SECURITY.md](SECURITY.md).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support, please see [SUPPORT.md](SUPPORT.md) or contact contact@voxhash.dev.

---

**HandForge** - Audio & Video conversion made simple  
© 2026 VoxHash Technologies
