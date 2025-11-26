# Installation Guide

This guide provides detailed installation instructions for HandForge on different platforms.

## System Requirements

- **Python**: 3.9 or higher
- **FFmpeg**: Latest stable version
- **Operating System**: Windows 10+, Linux (most distributions), macOS 10.14+

## Python Installation

### Windows

1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run the installer
3. Check "Add Python to PATH" during installation
4. Verify: `python --version`

### Linux

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip

# Verify
python3 --version
```

### macOS

```bash
# Using Homebrew
brew install python3

# Or download from python.org
```

## FFmpeg Installation

### Windows

**Option 1: Using winget**
```bash
winget install ffmpeg
```

**Option 2: Manual Installation**
1. Download from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add `C:\ffmpeg\bin` to your system PATH
4. Verify: `ffmpeg -version`

### Linux

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

### macOS

```bash
# Using Homebrew
brew install ffmpeg
```

## HandForge Installation

### Step 1: Clone or Download

```bash
git clone https://github.com/VoxHash/HandForge.git
cd HandForge
```

Or download and extract the ZIP file.

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

Or using a virtual environment (recommended):

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Verify Installation

```bash
# Check Python version
python --version

# Check FFmpeg
ffmpeg -version

# Check PyQt6
python -c "import PyQt6; print('PyQt6 installed successfully')"
```

## Running HandForge

```bash
python -m handforge.app
```

## Troubleshooting

### FFmpeg Not Found

- Ensure FFmpeg is in your system PATH
- Restart your terminal/command prompt after installing FFmpeg
- Verify with `ffmpeg -version`

### PyQt6 Installation Issues

```bash
# Try upgrading pip first
pip install --upgrade pip

# Then install PyQt6
pip install PyQt6
```

### Python Version Issues

- Ensure Python 3.9+ is installed
- Use `python3` instead of `python` on Linux/macOS if needed

## Next Steps

- [Getting Started](getting-started.md)
- [Usage Guide](usage.md)
- [Configuration](configuration.md)

---

**Installation complete!** You're ready to use HandForge.

