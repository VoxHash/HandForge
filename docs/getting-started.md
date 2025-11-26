# Getting Started with HandForge

This guide will help you get started with HandForge, from installation to your first audio or video conversion.

## Prerequisites

Before installing HandForge, ensure you have:

- **Python 3.9 or higher** installed
- **FFmpeg** installed and available in your system PATH
- **pip** (Python package manager)

## Installation

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Install FFmpeg

#### Windows

```bash
winget install ffmpeg
```

Or download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

#### Linux

```bash
sudo apt install ffmpeg
```

#### macOS

```bash
brew install ffmpeg
```

### Step 3: Verify Installation

```bash
# Verify Python
python --version

# Verify FFmpeg
ffmpeg -version

# Verify PyQt6
python -c "import PyQt6; print('PyQt6 installed')"
```

## Running HandForge

### Basic Usage

```bash
python -m handforge.app
```

The application window should open, and you're ready to start converting audio and video files!

## Your First Conversion

1. **Add Files**: Click "Add Files" or drag and drop audio/video files into the queue
2. **Select Preset**: Choose a conversion preset from the dropdown (e.g., "MP3 192k" for audio, "MP4 H.264" for video)
3. **Configure Options**: For video files with subtitles, select subtitle track in the queue table
4. **Start Conversion**: Click the "Start Conversion" button
5. **Monitor Progress**: Watch the progress bars with ETA in the Active Conversions table
6. **Find Output**: Converted files are saved to `~/HandForge_Output` by default (or `%USERPROFILE%\HandForge_Output` on Windows). Location is shown in status bar when conversion completes.

## Next Steps

- Read the [Usage Guide](usage.md) for detailed instructions
- Check out [Configuration](configuration.md) to customize HandForge
- Explore [Examples](examples/) for common use cases
- Visit [Troubleshooting](troubleshooting.md) if you encounter issues

## Getting Help

- [FAQ](faq.md) - Common questions
- [Troubleshooting](troubleshooting.md) - Problem solving
- [Support](../SUPPORT.md) - Additional support options

---

**Welcome to HandForge!** We hope you enjoy using it.

