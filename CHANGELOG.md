# Changelog — HandForge

All notable changes to HandForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Modern media desktop shell: sidebar library chrome (Convert / Queue / Active Jobs / Library / Preferences), forge charcoal + copper theme, bundled Manrope typeface, stage cross-fade and nav indicator motion; Convert workspace preserves queue + active jobs; see [docs/desktop.md](docs/desktop.md)
- CI packaging for desktop wheels: `.github/workflows/packaging.yml` builds sdist + wheel on push/PR/tags, runs `twine check`, verifies `handforge/resources/*.png` and `handforge` / `handforge-gui` entry points, uploads `dist/` artifacts; tag builds attach packages to the GitHub Release; optional PyPI publish via Trusted Publishing (OIDC) when repo variable `PYPI_TRUSTED_PUBLISHING=true` (no API token secrets); local verify with `python -m build` / `tests/test_packaging.py`; see [docs/desktop.md](docs/desktop.md)
- Linux FreeDesktop launcher: `handforge install-desktop` (or `scripts/install-desktop.sh`) installs `dev.voxhash.HandForge.desktop` + hicolor icons under `~/.local/share` (optional `--system` / `--prefix` / `--uninstall`); `handforge-gui` console script for absolute `Exec=`; template in `packaging/linux/handforge.desktop`; see [docs/desktop.md](docs/desktop.md)
- Desktop GUI / system-tray icon: multi-size PNGs in `handforge/resources/`, `handforge.util.icons` loads them (QPainter fallback if missing), window + tray + `QApplication` icon set before tray `show()`; regenerate with `scripts/generate-app-icons.py`; package-data includes `resources/*.png`; see [docs/desktop.md](docs/desktop.md)
- Desktop install & usage guide for Windows / Linux / macOS: canonical project `.venv`, `pip install -e .`, FFmpeg per OS, GUI and CLI post-install paths in [docs/desktop.md](docs/desktop.md); ROADMAP **E2E Workflow & Ops** milestone; linked from README, docs index, installation, getting-started, quick-start
- On-headset heavy encodes for Meta Quest: reuse Android companion APK on Quest (Horizon OS is Android) — `LocalEncodeActivity` with `tier: "heavy"` presets (720p HQ / 1080p / 8 Mbps capture + high-bitrate audio), Quest chrome + thermal note, `HandForgeNative` JS bridge from `/quest.html` WebView; Quest Browser still drives LAN host encode; docs in `companions/quest/` + `docs/companions.md`; pytest + Kotlin unit coverage
- Bundled multi-ABI `libffmpeg.so` for the Android companion: `scripts/fetch-android-ffmpeg.sh` downloads SHA256-pinned husen-hn FFmpeg 7.1 prebuilts into `jniLibs/` (`armeabi-v7a`, `arm64-v8a`; optional `x86_64`); large blobs gitignored; LocalEncode uses bundled ProcessBuilder path when libs are present (Termux remains fallback); `extractNativeLibs=true`; unit tests for bundled argv / Termux extras; optional CI `workflow_dispatch` fetch; see [companions/android/README.md](companions/android/README.md)
- Quest / store HTTPS packaging for Meta Horizon 2D PWA: Bubblewrap templates (`companions/quest/bubblewrap/`, `horizonOSAppMode: 2D`), `scripts/quest-https-package.sh` (configure / publish-assetlinks / build / verify), `quest.webmanifest`, unauthenticated `GET /.well-known/assetlinks.json`, Caddy/nginx TLS reverse-proxy examples; LAN HTTP Quest Browser path unchanged; see [docs/examples/example-03.md](docs/examples/example-03.md)
- On-device Android FFmpeg encode in the GrapheneOS companion APK: SAF media pick, stage under `Download/HandForge/`, curated presets (`encode_presets.json`), Termux `RUN_COMMAND` backend (`pkg install ffmpeg` + `allow-external-apps`) and optional bundled `libffmpeg.so` path; JDK 17 CI workflow `.github/workflows/android-companion.yml`; pytest coverage in `tests/test_ondevice_presets.py`
- Crash-safe conversion queue persistence: atomic `~/.handforge/queue.json` stores pending/queued/active jobs (+ light session meta); GUI and `handforge serve` restore unfinished work on startup; clearing an empty queue removes the file (`handforge/core/queue_persist.py`)
- Companion live status push: token-gated `GET /api/events` Server-Sent Events from `QueueStatusHub`; phone/Quest UIs use EventSource first and keep 1s `/api/status` polling as fallback
- Android / GrapheneOS companion scaffold (`companions/android/`): PWA connector + native WebView APK (Gradle/Kotlin, **no Google Play Services**); optional Capacitor `package.json` / `www/`; sideload-oriented; see [docs/companions.md](docs/companions.md)
- Meta Quest 3 companion UI (`/quest.html`) with large hit targets and shared control; docs in `companions/quest/`; Quest Browser → LAN HandForge host
- Real-time conversion preview: `POST /api/control/preview` runs real FFmpeg for short audio/video clips + thumbnails (`handforge/companion/preview.py`); companion UI preview panel
- Collaborative preset sharing over LAN: `GET /api/presets`, `/api/presets/export`, `POST /api/presets/import` (`handforge/companion/share.py`); token-gated; no cloud
- Advanced analytics reporting: `build_aggregate_report` / companion `GET /api/analytics/report` / CLI `list-analytics --report` (local-only aggregates)
- Companion PWA assets: `manifest.webmanifest`, service worker, icons; install from phone browser / Vanadium
- Watch-folder / hotfolder auto-convert: CLI `handforge watch` polls directories for new stable media, tracks `~/.handforge/seen_files.json`, converts via Orchestrator (`handforge/util/watchfolder.py`)
- Shared workstation web UI on the companion server: mobile/desktop control page plus mutating `/api/control/*` (start/stop, add/remove jobs, clear pending, output dir / preset / format / bitrate) wired to a live `SessionController` → Orchestrator; **writes always require `companion_token`** (403 if unset); LAN risk notes in Preferences / `serve` / docs; `handforge serve` runs a controllable session (not status-only)
- Companion remote queue monitoring (`handforge/companion/`): **opt-in** local HTTP server + mobile-friendly web UI for phone/LAN monitoring of real Orchestrator queue, active jobs, and progress (default OFF, bind `127.0.0.1:8765`); shared token required for non-localhost / `--lan`; Preferences → Advanced → **Companion**; CLI `handforge serve` and `convert --companion` / `--companion-lan`; `GET /api/status` (+ `?token=`); PWA-friendly browser companion for now — native store apps remain future
- Optional performance analytics (`handforge/util/analytics.py`): **opt-in, local-only** (default OFF) — records real per-job and batch metrics (FFmpeg encode speed, wall duration, throughput, peak parallel, ETA mean absolute error) under `~/.handforge/analytics/batches.jsonl`; nothing is uploaded; Preferences → Advanced → **Enable performance analytics (local only)**; CLI `convert --analytics` / `--no-analytics` prints a summary after the batch; `list-analytics` shows recent history; GUI status bar / tray show a one-line summary when enabled
- Cloud storage integration (`handforge/util/cloud.py`): configure **local sync folders** (Dropbox / Google Drive / OneDrive / Nextcloud mounts + custom roots) for pick-up and save; optional **rclone** backend when installed (`listremotes`, stage `remote:path` inputs, upload outputs) with clear messaging when rclone is absent — no fake API keys; Preferences → **Cloud**; CLI `list-cloud`, `convert --cloud-remote` / `--cloud-output` / `--no-rclone`; GUI Add Files/Folder starts in `cloud_input_root` and respects `output_dir` including cloud roots
- Plugin system architecture (`handforge/plugins/`): discover plugins from `~/.handforge/plugins`, `HANDFORGE_PLUGIN_DIRS` / `plugin_dirs`, and packaging entry points (`handforge.plugins`); register **presets** (merged into `all_presets()`) and **pre/post-convert hooks** (wired in Orchestrator workers); example plugin `examples/plugins/archive_flac_sidecar/`; CLI `list-plugins`; docs in [docs/plugins.md](docs/plugins.md); off path unchanged when no plugins load
- Video filters via real FFmpeg chains (`handforge/util/video_filters.py`): **brightness / contrast / saturation** (`eq`) and single-pass **stabilization** (`deshake`); Preferences → Video; CLI `convert --video-color` / `--brightness` / `--contrast` / `--saturation` / `--stabilize` (and `--stabilize-rx` / `--stabilize-ry`); off by default; software filters run before HW upload so NVENC/QSV/VAAPI paths stay valid
- Advanced audio filters via real FFmpeg chains (`handforge/util/audio_filters.py`): 3-band **EQ** (`equalizer`), **compressor** (`acompressor`), **limiter** (`alimiter`), and **noise reduction** (`afftdn`); Preferences → Audio; CLI `convert --eq` / `--compressor` / `--limiter` / `--denoise` (and related params); all off by default so existing encodes are unchanged
- Hardware-accelerated video encoding: probe local FFmpeg for **NVENC**, **Intel Quick Sync**, **VAAPI**, and **VideoToolbox**; Preferences **Hardware Acceleration** (Auto / Software / NVENC / Quick Sync / VAAPI / VideoToolbox); CLI `list-hw-accel` and `convert --hw-accel`; Auto picks a working backend and workers fall back to libx264/libx265 if HW encode fails (`handforge/util/hwaccel.py`)
- Optional Rust adaptive parallel scheduler (`native/handforge_scheduler`) that caps concurrent FFmpeg jobs from free RAM and load; pure-Python fallback when the cdylib is not built
- Preferences toggle **Adapt concurrency from free RAM / CPU load** (`adaptive_parallel`, default on)
- Comprehensive pytest suite: unit coverage for progress, native scheduler, settings, Job model, FFmpeg command helpers, and orchestrator adaptive concurrency; integration tests that run real FFmpeg pipelines on lavfi-generated audio/video clips (skipped when FFmpeg is missing)
- Headless CLI for batch conversion: `python -m handforge` / console script `handforge` (`convert`, `list-presets`); reuses Orchestrator workers and FFmpeg helpers; progress on stderr, output paths on stdout, non-zero exit on failure; no DISPLAY required
- Preset template library: curated templates (Apple Podcasts / YouTube-aligned bitrates and common archive workflows) in `handforge/data/preset_templates.json`; GUI **Settings → Preset Template Library**; Manage Presets import/export JSON; CLI `list-templates`, `apply-template`, `export-presets`, `import-presets`; `convert --preset` accepts template ids/names without installing
- Actionable error messages (`handforge.util.errors`): shared classifier maps common conversion failures (missing FFmpeg, disk full, permissions, missing/corrupt input, unsupported encoder/decoder/muxer, filter errors, timeouts, incomplete/missing video output) to a short summary plus numbered **What to try** steps; unit tests in `tests/test_errors.py`
- Keyboard shortcuts for common GUI actions (add files/folder, start/stop, clear queue, preferences, presets, focus queue/active conversions, quit); **Help → Keyboard Shortcuts** (`F1`); documented in [docs/usage.md](docs/usage.md); tests in `tests/test_shortcuts.py`

### Changed
- Orchestrator respects `adaptive_parallel`: user `parallel` setting is a hard ceiling; effective concurrency can be lower under memory/load pressure
- Conversion failures in the orchestrator are enriched before GUI/CLI display; Active Conversions log dialog and status tooltips show solutions; CLI prints multi-line guidance on FAIL and pre-flight write checks use the same mapper

### Fixed
- GUI system tray no longer calls `QSystemTrayIcon.show()` without an icon (`QSystemTrayIcon::setVisible: No Icon set`); removed duplicate tray created in `handforge/app.py` (MainWindow owns the tray)
- Parallel workers no longer collide on the shared `.handforge_test_<pid>` write-permission probe (include worker id)
- Short/fast FFmpeg jobs that finish within 0.1s are no longer treated as immediate failures when exit code is 0
- Progress under heavy parallel load: keepalive no longer resets bars to 0.1%; progress stays monotonic; ETA uses FFmpeg `speed=`; Preferences `ewma_alpha` now smooths %/ETA; UI coalesces table redraws and shows aggregate batch progress
- Failed FFmpeg jobs now classify from the buffered stderr log (not a second empty `stderr.read()`), so codec/permission hints are not lost

## [1.3.2] - 2026-10-05

### Added
- Right-click context menu on Active Conversions: **Play Media** and **Open Output Folder** ([68ee076](https://github.com/VoxHash/HandForge/commit/68ee076257effa747bbb8b1b0195f94ecd7155f3))

### Changed
- Active Conversions **File** column shows output filename with the target extension
- Output directories created with explicit `0o755` permissions when missing

### Fixed
- Permission denied errors when writing to the output directory (pre-conversion checks, test writes, and automatic permission repair when possible) ([68ee076](https://github.com/VoxHash/HandForge/commit/68ee076257effa747bbb8b1b0195f94ecd7155f3))
- Safer overwrite handling when the destination file already exists

### Removed
- Removed obsolete `DEVELOPMENT_GOALS.md` (planning tracked in ROADMAP and GitHub Issues)

## [1.3.1] - 2026-03-12

### Fixed
- **CRITICAL**: Fixed video stream loss in video-to-video conversions (MKV to MP4, size reduction)
  - Prevented `-vn` flag from being added when converting video to video
  - Added safety check to never extract audio when `reduce_size` is enabled
  - Improved destination format detection to check format extension if path doesn't exist
  - Explicitly ensure `extract_audio_only` is False for video-to-video conversions
  - Added video stream verification using ffprobe to detect missing video streams
- Fixed `speed_str` undefined variable error in orchestrator
- Fixed duplicate `checkbox_two_pass` widget addition
- Fixed duplicate `is_failed` variable definition
- Fixed variable name collision for `remaining` in progress tracking
- Fixed undefined `elapsed` variable in some code paths
- Fixed completion message showing "successful" even when conversions failed
- Improved output file size validation (100KB minimum for video files vs 1KB for audio)

## [1.3.0] - 2026-03-12

### Added
- **macOS Support**: Full macOS compatibility with Apple Silicon and Intel support
  - Added macOS-specific FFmpeg path detection (`/opt/homebrew/bin` for Apple Silicon, `/usr/local/opt/ffmpeg/bin` for Intel)
  - Added macOS to CI/CD testing matrix
  - Updated all documentation to include macOS alongside Windows and Linux

### Added
- **Multi-Language Support (i18n)**: Full internationalization with 11 languages
  - English (en), Russian (ru), Portuguese (pt), Spanish (es), Estonian (et)
  - French (fr), German (de), Japanese (ja), Chinese (zh), Korean (ko), Indonesian (id)
- **Language Selection**: Language selector in Preferences dialog with auto-detect option
- **Status Column Click Handler**: Click Status column to view error log for failed conversions
- **Progress Bar Color Coding**: Failed conversions show red progress bar
- **Clear Active Conversions**: Menu option to clear completed/failed items from Active Conversions table

### Changed
- **Error Message Display**: Cleaned up duplicate "Error:" prefixes in status messages
- **UI Button Location**: Moved "Clear Active Conversions List" to File menu
- **Progress Bar Styling**: Failed conversions display with red color scheme

### Fixed
- Fixed signal signature mismatch (`sig_done` missing `output_path` parameter)
- Fixed error message formatting (removed duplicate "Error:" prefixes)
- Fixed progress bar color for failed conversions (now shows red)

### Technical
- Added `handforge/i18n/` module with translator system
- Created translation files for all 11 supported languages
- Integrated i18n throughout main window UI
- Added language persistence in settings

## [1.2.0] - 2025-01-XX

### Added
- **Preferences Dialog**: Comprehensive settings dialog with tabbed interface
  - General settings (parallel processing, file handling, system tray)
  - Conversion settings (output directory, codec threads)
  - Audio settings (loudness normalization, cover art preferences)
  - Video settings (default quality, codec, size reduction defaults)
  - Advanced settings (auto-retry, performance tuning)
- **Audio Trimming**: Trim audio files by start/end time
- **Audio Effects**: Fade in/out effects for audio files
- **Video Trimming**: Trim video files by start/end time
- **Video Cropping**: Crop video to specific region
- **Resolution Scaling**: Scale video resolution with quality preservation
- **Frame Rate Conversion**: Convert video frame rates
- **Video Quality Presets**: Low, medium, high, ultra quality presets
- **Multiple Audio Track Handling**: Select specific audio tracks from multi-track videos
- **Audio Quality Analysis**: Analyze audio quality metrics (codec, bitrate, sample rate, channels)
- **System Tray Integration**: Minimize to system tray with notifications
- **Progress Notifications**: System tray notifications for conversion completion
- **Better Progress Parsing**: Real-time progress parsing from FFmpeg stderr output

### Changed
- **Progress Tracking**: Improved progress calculation using actual FFmpeg time/duration data
- **Settings Management**: Centralized settings in Preferences dialog
- **Window Close Behavior**: Configurable minimize-to-tray on window close

### Technical
- Added `get_audio_tracks()` function for multi-track video support
- Added `get_media_info()` and `analyze_audio_quality()` functions
- Enhanced FFmpeg command building with new audio/video options
- Improved progress parsing with regex-based time extraction

## [1.1.0] - 2025-01-XX

### Added
- **Video Conversion Support**: Full video format conversion (MP4, MKV, AVI, MOV, WebM, etc.)
- **Video to Audio Extraction**: Extract audio tracks from video files
- **Per-File Subtitle Selection**: Select subtitle tracks individually for each video file in the queue
- **Smart Video Compression**: Reduce video file size by 5-10x using H.265/HEVC codec while maintaining quality
- **Two-Pass Encoding**: Optional two-pass encoding for optimal quality/size ratio
- **Progress Bar with ETA**: Visual progress bars showing percentage and estimated time remaining
- **Queue Management**: Files remain visible in queue until processing starts
- **File Save Location Display**: Shows where converted files are saved upon completion
- **View Log Dialog**: Clickable log viewer showing conversion logs and output file paths
- **PyQt6 Migration**: Upgraded from PyQt5 to PyQt6 for better compatibility

### Changed
- **UI Improvements**: Enhanced glassmorphism design with better visual feedback
- **Queue Counter**: Accurate queue counter showing pending files (queue + orchestrator queue)
- **Column Layout**: Swapped Progress and Log columns in Active Conversions table
- **Progress Display**: Replaced text percentage with visual progress bar widgets

### Fixed
- Fixed file names not showing in Active Conversions table
- Fixed progress stuck at 99% by ensuring 100% is emitted on completion
- Fixed subprocess buffering warnings
- Fixed preset format detection with emoji prefixes
- Fixed queue counter accuracy

### Technical
- Migrated from PyQt5 to PyQt6
- Added FFprobe integration for subtitle track detection
- Improved FFmpeg command building for video conversions
- Enhanced worker thread management and progress tracking
- Better error handling and logging

## [1.0.0] - 2025-11-23

### Added
- Initial release of HandForge
- Batch queue system for audio conversion
- Support for multiple audio formats (mp3, aac, m4a, flac, wav, ogg, wma, etc.)
- CBR, VBR, and Lossless encoding modes
- Custom presets system with save/load functionality
- Metadata management (title, artist, album, year, genre)
- Cover art support (embedded and external)
- Parallel encoding with configurable thread counts
- Real-time progress tracking with ETA and speed
- Auto-retry system with configurable patterns
- Dark theme support
- Window state persistence
- Export/import presets and patterns (CSV/JSON)
- Drag & drop file support
- Queue filtering and search
- Workers table with detailed status
- Log viewer for failed conversions
- Resume pending items from previous session
- EBU R128 loudness normalization support
- Filename pattern parsing for metadata extraction
- Duplicate file handling (skip, overwrite, rename)

### Technical
- Built with PyQt6 for cross-platform GUI
- FFmpeg integration for audio processing
- JSON-based settings and presets storage
- Modular architecture with core, ui, dialogs, and util modules
