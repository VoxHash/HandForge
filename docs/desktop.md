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
handforge-gui
# equivalent:
python -m handforge.app
```

The GUI sets a packaged HandForge icon on the window and system tray before the tray is shown (so Qt does not warn `QSystemTrayIcon::setVisible: No Icon set`). Minimize-to-tray still follows Preferences → General.

### Linux application menu (`.desktop`)

After `pip install -e .`, register HandForge in the FreeDesktop app menu (user install, no root):

```bash
handforge install-desktop
# or from the repo without activating PATH:
./scripts/install-desktop.sh
```

This writes:

| Path | Purpose |
|------|---------|
| `~/.local/share/applications/dev.voxhash.HandForge.desktop` | Start-menu launcher |
| `~/.local/share/icons/hicolor/*/apps/dev.voxhash.HandForge.png` | Menu / taskbar icon |

`Exec=` uses the absolute path to `handforge-gui` next to the active interpreter (project `.venv` when you run from that venv), so the menu entry works without activating the shell. Options: `--dry-run`, `--uninstall`, `--system` (`/usr/share`, needs write access), `--prefix DIR`. Template (placeholders): [packaging/linux/handforge.desktop](../packaging/linux/handforge.desktop).

### Python wheels / CI packaging

The project ships as a pure-Python wheel (PyQt6 dependency). Package data includes `handforge/resources/*.png` (tray/window icons) and `handforge/resources/fonts/*` (bundled UI typeface) via `[tool.setuptools.package-data]` in `pyproject.toml`.

**Local build** (from a project venv):

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
# Inspect: unzip -l dist/handforge-*.whl | grep resources
```

**CI**: [`.github/workflows/packaging.yml`](../.github/workflows/packaging.yml) runs on pushes/PRs to `main`/`develop` and on `v*` tags — builds sdist+wheel, `twine check`, asserts resources + `handforge` / `handforge-gui` console scripts, uploads the `python-package-distributions` artifact. Tag pushes also attach `.whl` / `.tar.gz` to the GitHub Release (alongside the notes workflow).

**PyPI (optional)**: no API token is stored in the repo. To enable Trusted Publishing, create a PyPI publisher for this workflow + GitHub Environment `pypi`, then set repository variable `PYPI_TRUSTED_PUBLISHING=true`. Until then, download the CI artifact (or use local `dist/`) and publish manually:

```bash
python -m twine upload dist/*
```

Linux tip: if you are on a remote/SSH session but have a local display:

```bash
DISPLAY=:0 handforge-gui
```

### First conversion in the GUI

The desktop shell uses a left **sidebar** (Convert, Queue, Active Jobs, Library, Preferences) and a main **stage**. Convert is the day-to-day workspace: file controls, preset picker, queue, and active jobs side by side.

1. Open the **Convert** sidebar section (default).
2. **Add Files** or **Add Folder** (or drag-and-drop into the Conversion Queue).
3. Choose a **preset** (audio or video) from the preset control on Convert.
4. Confirm the **output directory** (default `~/HandForge_Output`, or `%USERPROFILE%\HandForge_Output` on Windows) under **Settings → Preferences → Conversion** (or the Preferences sidebar item).
5. Click **Start Conversion** (shortcut: Ctrl+Return). The shell emphasizes **Active Jobs**.
6. Watch progress in **Active Conversions**; open the output folder from the status bar / context menu when done.

**Sidebar shortcuts**

| Sidebar | What it does |
|---------|----------------|
| Convert | Full convert workspace (add → preset → start) |
| Queue | Focus Conversion Queue (`Ctrl+1`) |
| Active Jobs | Focus Active Conversions (`Ctrl+2`) |
| Library | Presets, template library, patterns, auto-retry |
| Preferences | Opens Preferences (`Ctrl+,`) |

Useful menus after install:

| Action | Where |
|--------|--------|
| Preferences | Sidebar **Preferences**, or Settings → Preferences (Ctrl+,) |
| Preset template library | Sidebar **Library**, or Settings → Preset Template Library |
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
3. GUI: `handforge-gui` / `python -m handforge.app` (Linux menu: `handforge install-desktop`) — or CLI: `handforge convert …`.
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
| Tray shows blank / `No Icon set` | Reinstall editable package so `handforge/resources/*.png` is included (`pip install -e .`); icons regenerate via `python scripts/generate-app-icons.py` (Pillow) |
| App menu entry missing / wrong Python | Re-run `handforge install-desktop` from the `.venv` you use day-to-day; check `Exec=` in `~/.local/share/applications/dev.voxhash.HandForge.desktop` |

More cases: [troubleshooting.md](troubleshooting.md).

## 8. Cloud backup (ops)

Local sync folders and optional rclone are covered in [cloud.md](cloud.md). For **Proton Drive**:

1. Install / authenticate the real CLI: `proton-drive auth login` (optional: run `proton-drive-desktop`).
2. Preferences → **Cloud → Proton Drive backup** (opt-in) or CLI `handforge backup-proton` / `convert --proton-backup`.
3. Confirm with `handforge list-cloud` (shows Proton Drive auth + remote folder).

HandForge does not store Proton credentials.

## Related docs

- [Installation (reference)](installation.md)
- [Getting started](getting-started.md)
- [Usage (GUI)](usage.md)
- [Cloud & Proton Drive](cloud.md)
- [CLI](cli.md)
- [Quick start](quick-start.md)

---

© 2026 VoxHash Technologies — contact@voxhash.dev
