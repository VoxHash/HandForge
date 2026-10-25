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
- **Parallel Processing**: Parallel encodes with per-codec thread caps and optional Rust adaptive scheduling (RAM/load aware)
- **Presets System**: Save and load custom conversion presets (audio and video)
- **Preset Template Library**: Curated Podcast / Speech / Music / Archive / Video templates (browse/apply in GUI; CLI `list-templates` / `apply-template`)
- **Metadata Management**: Copy or strip metadata, per-file overrides
- **Multi-Language Support**: Full internationalization with 11 languages
- **System Tray**: Minimize to tray with conversion notifications
- **Real-time Progress**: Progress tracking with elapsed/ETA/speed and visual progress bars
- **Headless CLI**: Batch convert from the terminal (`python -m handforge`) without a GUI or display
- **Companion monitor**: Opt-in local HTTP + mobile web UI to watch queue/active progress from a phone on the LAN (`handforge serve` / Preferences → Companion)

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

# 3) Run the GUI
python -m handforge.app

# Or convert headlessly (no display required)
python -m handforge convert input.mp3 --preset "MP3 192k" -o ./output
python -m handforge list-presets
python -m handforge list-templates --category Podcast -v
python -m handforge apply-template podcast-aac-128
```

## 💿 Installation

See [docs/installation.md](docs/installation.md) for platform-specific installation instructions.

Optional native scheduler (reduces peak RAM under heavy batches):

```bash
cd native/handforge_scheduler && cargo build --release
```

## 🛠 Usage

**GUI**: Add files to the queue, select a preset, and start conversion. Details: [docs/usage.md](docs/usage.md).

**CLI** (same conversion stack, headless): [docs/cli.md](docs/cli.md).

```bash
python -m handforge convert ./folder --preset "AAC 256k" --output-dir ./out --parallel 2
```

### Supported Formats

**Audio**: mp3, m4a/aac, opus, ogg/vorbis, flac, alac, wav, aiff, wma, ac3/eac3, ape, tta, wavpack, mp2, amr, caf, au, mka and more

**Video**: mp4, mkv, avi, mov, wmv, flv, webm, m4v, 3gp, ogv, mts, m2ts, ts, and more

## ⚙️ Configuration

Key settings (full reference: [docs/configuration.md](docs/configuration.md)):

| Setting | Description | Default |
|---------|-------------|---------|
| `parallel` | Max parallel encodes (hard ceiling) | 2 |
| `adaptive_parallel` | Lower concurrency from free RAM/load | true |
| `output_dir` | Default output directory (may be a local cloud sync folder) | ~/HandForge_Output |
| `cloud_roots` | Local sync / mount folders for pick-up and save | `[]` |
| `rclone_remote` | Optional default rclone remote name | `""` |
| `performance_analytics` | Opt-in local batch metrics (`~/.handforge/analytics/`) | false |
| `companion_enabled` | Opt-in remote queue monitor HTTP + mobile web UI | false |
| `companion_host` / `companion_port` | Companion bind (default localhost:8765; LAN needs token) | `127.0.0.1` / `8765` |
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

We welcome PRs! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and follow the PR template. Run `pytest` (requires FFmpeg on PATH for integration tests) before opening a PR.

## 🔒 Security

Please report vulnerabilities via [SECURITY.md](SECURITY.md).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support, please see [SUPPORT.md](SUPPORT.md) or contact contact@voxhash.dev.

---

**HandForge** - Audio & Video conversion made simple  
© 2026 VoxHash Technologies
