# Desktop install & usage (Windows, Linux, macOS)

End-to-end guide for installing HandForge on any supported desktop OS and using it after install. HandForge is a Python + PyQt6 + FFmpeg app; the same tree runs the GUI and the headless CLI.

**Supported desktops:** Windows 10+, Linux (most distributions with a desktop or headless CLI), macOS 10.14+ (Apple Silicon and Intel).

**Contact:** VoxHash Technologies — contact@voxhash.dev

## Requirements

| Component | Notes |
|-----------|--------|
| Python 3.9+ | On PATH as `python` / `python3` |
| FFmpeg | On PATH; verify with `ffmpeg -version` |
| Display (GUI only) | Wayland/X11 on Linux, normal desktop session on Windows/macOS |
| Optional: Rust toolchain | Only if you build the adaptive parallel scheduler |

## 1. Install FFmpeg

### Windows

```powershell
winget install ffmpeg
```

Or download a build from [ffmpeg.org](https://ffmpeg.org/download.html), extract it, and add the `bin` folder to your user `PATH`. Open a **new** terminal and check:

```powershell
ffmpeg -version
```

### Linux

```bash
# Debian / Ubuntu
sudo apt update && sudo apt install -y ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

```bash
ffmpeg -version
```

### macOS

```bash
brew install ffmpeg
ffmpeg -version
```

## 2. Get the source

```bash
git clone https://github.com/VoxHash/HandForge.git
cd HandForge
```

Or download the ZIP from GitHub and extract it, then `cd` into the project root (the folder that contains `pyproject.toml` and `handforge/`).

## 3. Create the project virtualenv and install HandForge

Use a project-local `.venv` so the `handforge` console script and GUI share one install.

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

If execution policy blocks activation:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Or call the venv without activating:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

### Linux / macOS (bash/zsh)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

`requirements.txt` currently pins the GUI dependency (`PyQt6`). `pip install -e .` registers the `handforge` console script from `pyproject.toml`.

### Verify the install

```bash
python --version
ffmpeg -version
python -c "import PyQt6; import handforge; print('HandForge OK')"
handforge --version
handforge --help
```

On Windows, if the shell was not activated, use `.\.venv\Scripts\handforge.exe --help` instead of `handforge`.

## 4. Optional: native adaptive scheduler

Builds a small Rust library that can lower parallel FFmpeg jobs under RAM/CPU pressure. Without it, HandForge uses a pure-Python fallback.

```bash
# Requires rustup: https://rustup.rs/
cd native/handforge_scheduler
cargo build --release
cd ../..
```

```bash
python -c "from handforge.core.native_scheduler import native_available, system_snapshot; print(native_available(), system_snapshot(4))"
```

## 5. Use after install — GUI

From the activated `.venv` (or with the venv `python` on PATH):

```bash
python -m handforge.app
```

Linux tip: if you are on a remote/SSH session but have a local display:

```bash
DISPLAY=:0 python -m handforge.app
```

### First conversion in the GUI

1. **Add Files** or **Add Folder** (or drag-and-drop into the queue).
2. Choose a **preset** (audio or video) from the toolbar / presets UI.
3. Confirm the **output directory** (default `~/HandForge_Output`, or `%USERPROFILE%\HandForge_Output` on Windows) under **Settings → Preferences → Conversion**.
4. Click **Start Conversion** (shortcut: Ctrl+Return).
5. Watch **Active Conversions**; open the output folder from the status bar / context menu when done.

Useful menus after install:

| Action | Where |
|--------|--------|
| Preferences | Settings → Preferences (Ctrl+,) |
| Preset template library | Settings → Preset Template Library |
| Keyboard shortcuts | Help → Keyboard Shortcuts (F1) |
| Companion / LAN control | Preferences → Advanced → Companion |

Full GUI feature walkthrough: [usage.md](usage.md).

## 6. Use after install — CLI (no display required)

All of these use the same Orchestrator / FFmpeg stack as the GUI.

```bash
# List presets and templates
handforge list-presets
handforge list-templates --category Podcast -v

# Install a curated template into ~/.handforge/presets.json
handforge apply-template podcast-aac-128

# Convert files or a folder
handforge convert ./input.mp3 --preset "MP3 192k" -o ./output
handforge convert ./folder --preset "AAC 256k" --output-dir ./out --parallel 2

# Probe hardware encoders on this machine
handforge list-hw-accel

# Opt-in companion HTTP (localhost by default)
handforge serve
handforge serve --lan   # bind for LAN; control writes need the shared token

# Watch-folder / hotfolder
handforge watch ~/Inbox -o ~/HandForge_Output -f mp3 --bitrate 192 --once
```

Module form (equivalent if the console script is not on PATH):

```bash
python -m handforge convert ./input.mp3 --preset "MP3 192k" -o ./output
```

Full CLI reference: [cli.md](cli.md). Settings file and keys: [configuration.md](configuration.md).

## 7. Day-to-day checklist

1. Activate `.venv` (or call `.venv`’s `python` / `handforge` directly).
2. Confirm `ffmpeg -version` still works after OS updates.
3. GUI: `python -m handforge.app` — or CLI: `handforge convert …`.
4. Outputs land in the configured output directory; queue can persist in `~/.handforge/queue.json` across restarts.
5. Companion / Quest / Android shells are separate from desktop install — see [companions.md](companions.md).

## Troubleshooting (desktop)

| Symptom | What to try |
|---------|-------------|
| `ffmpeg: command not found` | Reinstall FFmpeg; restart the terminal; fix PATH |
| `No module named PyQt6` / `handforge` | Activate `.venv`, then `pip install -r requirements.txt` and `pip install -e .` |
| GUI does not open on Linux | Check `echo $DISPLAY`; for a local seat try `DISPLAY=:0`; headless machines can still use `handforge convert` |
| `handforge: command not found` | Use `python -m handforge …` or ensure `.venv` is activated after `pip install -e .` |
| Permission errors writing output | Change output dir in Preferences, or pick a writable folder with `-o` / `--output-dir` |

More cases: [troubleshooting.md](troubleshooting.md).

## Related docs

- [Installation (reference)](installation.md)
- [Getting started](getting-started.md)
- [Usage (GUI)](usage.md)
- [CLI](cli.md)
- [Quick start](quick-start.md)

---

© 2026 VoxHash Technologies — contact@voxhash.dev
