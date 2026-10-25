# Installation Guide

Detailed installation for HandForge on Windows, Linux, and macOS. For a single end-to-end walkthrough (install **and** first use of GUI + CLI), prefer [Desktop install & usage](desktop.md).

## System Requirements

- **Python**: 3.9 or higher
- **FFmpeg**: On `PATH` (`ffmpeg -version`)
- **Operating System**: Windows 10+, Linux (most distributions), macOS 10.14+
- **GUI**: A display session (PyQt6). CLI works headless.

## Python Installation

### Windows

1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run the installer
3. Check **Add Python to PATH**
4. Verify: `python --version`

### Linux

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv

python3 --version
```

### macOS

```bash
brew install python3
# Or download from python.org
python3 --version
```

## FFmpeg Installation

### Windows

```powershell
winget install ffmpeg
```

Or download from [ffmpeg.org](https://ffmpeg.org/download.html), extract, add `bin` to PATH, then `ffmpeg -version`.

### Linux

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

### macOS

```bash
brew install ffmpeg
```

## HandForge Installation

### Step 1: Clone or download

```bash
git clone https://github.com/VoxHash/HandForge.git
cd HandForge
```

### Step 2: Project virtualenv (recommended)

Use `.venv` in the repo root so GUI and CLI share one install.

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

`pip install -e .` installs the package and the `handforge` / `handforge-gui` console scripts from `pyproject.toml`. Wheel builds include package data such as `handforge/resources/*.png` (see [Desktop — Python wheels / CI packaging](desktop.md#python-wheels--ci-packaging)).

### Step 3: Verify

```bash
python --version
ffmpeg -version
python -c "import PyQt6; import handforge; print('HandForge OK')"
handforge --version
```

## Running HandForge

```bash
# GUI
python -m handforge.app

# Headless CLI
handforge --help
python -m handforge convert input.mp3 --preset "MP3 192k" -o ./output
```

## Optional: Native Adaptive Scheduler (Rust)

```bash
cd native/handforge_scheduler
cargo build --release
```

Produces `target/release/libhandforge_scheduler.so` (Linux), `.dylib` (macOS), or `handforge_scheduler.dll` (Windows). Override path with `HANDFORGE_NATIVE_LIB` if needed.

```bash
python -c "from handforge.core.native_scheduler import native_available, system_snapshot; print(native_available(), system_snapshot(4))"
```

## Troubleshooting

### FFmpeg Not Found

- Ensure FFmpeg is on PATH; restart the terminal after install
- Verify with `ffmpeg -version`

### PyQt6 / handforge import issues

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

### Python Version Issues

- Require Python 3.9+
- On Linux/macOS prefer `python3` when creating the venv

## Next Steps

- [Desktop install & usage](desktop.md) — full install + post-install GUI/CLI
- [Getting Started](getting-started.md)
- [Usage Guide](usage.md)
- [CLI](cli.md)
- [Configuration](configuration.md)

---

**Installation complete.** Contact: contact@voxhash.dev — VoxHash Technologies.
