# Roadmap — HandForge

High-level milestones and planned features for HandForge.

## Q4 2026

### Performance & Stability
- ✅ Improve progress tracking accuracy under heavy parallel load (monotonic %, speed-aware ETA, EWMA, coalesced UI)
- ✅ Memory optimization for large batch conversions (adaptive parallel pool via optional Rust scheduler — see `native/handforge_scheduler`)
- ✅ Comprehensive unit and integration tests (pytest: progress, scheduler, settings, models, FFmpeg helpers, orchestrator; real FFmpeg lavfi pipelines when available)

### User Experience
- ✅ Command-line interface (CLI) for headless batch processing — see [docs/cli.md](docs/cli.md)
- ✅ Preset template library (curated templates + browse/apply/import/export in GUI and CLI)
- ✅ Improved error messages with actionable solutions — shared `handforge.util.errors` maps FFmpeg/FS failures to clear next steps in GUI (log dialog / tooltips) and CLI
- ✅ Keyboard shortcuts for common actions — QAction shortcuts (add/start/stop/prefs/presets/clear/focus); Help → Keyboard Shortcuts (`F1`); see [docs/usage.md](docs/usage.md)

## 2027

### Advanced Features
- ✅ Hardware acceleration support (NVENC, QuickSync, VAAPI)
- ✅ Advanced audio filters (EQ, compressor, limiter, noise reduction)
- ✅ Video filters (brightness, contrast, saturation, stabilization)
- ✅ Plugin system architecture for extensibility

### Platform & Integration
- ✅ Cloud storage integration (pick up / save to remote folders)
- ✅ Optional performance analytics for long batch jobs

## Future

### Platform Expansion
- ✅ Companion mobile apps (remote queue monitoring) — phase 1: opt-in local HTTP status API + mobile-friendly companion web UI (phone browser on LAN); Preferences + `handforge serve` / `convert --companion`; native app-store clients remain future
- ✅ Optional web-based interface for shared workstations — same companion server with shared-control UI + mutating `/api/control/*` (view queue, add/remove jobs, start/stop, output/preset); wired to live Orchestrator; writes always require `companion_token`; documented LAN risks; opt-in

#### Mobile & Headset Targets
These are **not** near-term ports of the desktop PyQt6 UI. They depend on a shared conversion/queue core (and the native scheduler path) before any full client ships. Phase-1 remote **queue monitoring** is covered by the companion web client above; the items below are the native shells / headset surfaces.

- ✅ **Android / GrapheneOS app** — PWA install + WebView APK scaffold under `companions/android/` (no Play Services; Vanadium WebView on GrapheneOS); Capacitor metadata optional; remote queue **control** against live Orchestrator API
- ✅ **On-device Android FFmpeg** — SAF pick + stage under `Download/HandForge/`; Termux `RUN_COMMAND` (`$PREFIX/bin/ffmpeg`) or optional bundled `libffmpeg.so`; curated presets in `encode_presets.json`; JDK 17 CI (`.github/workflows/android-companion.yml`)
- ✅ **Meta Quest 3 app** — Quest-friendly UI at `/quest.html` + `companions/quest/` docs; Quest Browser → LAN companion (large hit targets, shared control); LAN HTTP is the supported path; on-headset encodes via Android companion APK
- ✅ **Quest / store HTTPS packaging** — Bubblewrap / Horizon 2D TWA kit (`companions/quest/bubblewrap/`, `scripts/quest-https-package.sh`); `quest.webmanifest` + public `/.well-known/assetlinks.json`; TLS reverse-proxy examples; LAN HTTP remains supported
- ✅ **Bundled multi-ABI libffmpeg.so in APK** — `scripts/fetch-android-ffmpeg.sh` downloads pinned husen-hn FFmpeg 7.1 zips into `jniLibs/` (`armeabi-v7a` + `arm64-v8a`, optional `x86_64`); blobs gitignored; LocalEncode bundled backend + Termux fallback; optional CI workflow_dispatch fetch
- ✅ **On-headset heavy encodes** — Quest reuses Android companion `LocalEncodeActivity` + heavy presets (`encode_presets.json` tier `heavy`); `/quest.html` `HandForgeNative` bridge in APK WebView; thermal limits documented; LAN host remains primary for huge jobs

### Advanced Capabilities
- ✅ Real-time preview of conversions — FFmpeg short clip / thumbnail via `POST /api/control/preview` + companion UI (`handforge/companion/preview.py`)
- ✅ Collaborative features (preset sharing) — LAN export/import of custom presets (`/api/presets/*`, `handforge/companion/share.py`); token-gated; no cloud
- ✅ Advanced analytics and reporting — aggregate local report (`build_aggregate_report`, companion `/api/analytics/report`, CLI `list-analytics --report`)

## 2027 Continuity

### Automation
- ✅ Watch-folder / hotfolder auto-convert — CLI `handforge watch` polls directories, settles size/mtime, tracks `seen_files.json`, converts via Orchestrator (`handforge/util/watchfolder.py`)
- ✅ Crash-safe queue persistence across GUI/CLI restarts — atomic `~/.handforge/queue.json` (`handforge/core/queue_persist.py`); GUI + `handforge serve` restore pending/queued/active on startup; empty/cleared queues remove the file
- ✅ Companion live updates (SSE/WebSocket) instead of 1s polling — `GET /api/events` Server-Sent Events (token auth); `index.html` / `quest.html` prefer EventSource with 1s `/api/status` polling fallback

### Mobile encode & packaging
- ✅ On-device Android FFmpeg (Termux + SAF storage UX + encode presets + JDK 17 APK CI) — see `companions/android/`
- ✅ Quest / store HTTPS packaging (Bubblewrap against a public TLS origin) — see `companions/quest/bubblewrap/`
- ✅ Ship multi-ABI bundled `libffmpeg.so` inside the APK (`scripts/fetch-android-ffmpeg.sh` + jniLibs layout; Termux fallback)
- ✅ On-headset heavy encodes on Quest (Android APK LocalEncode + heavy presets; see `companions/quest/`)

## E2E Workflow & Ops

Next-phase ops/docs milestone after feature ROADMAP items are complete: make desktop install and day-to-day use reliable for any compatible OS.

- ✅ **Desktop install + usage guide (Windows / Linux / macOS)** — end-to-end project `.venv` + `pip install -e .`, FFmpeg per OS, GUI (`python -m handforge.app`) and CLI (`handforge` / `python -m handforge`) post-install use; [docs/desktop.md](docs/desktop.md); linked from [docs/index.md](docs/index.md), [README.md](README.md), [docs/installation.md](docs/installation.md), [docs/getting-started.md](docs/getting-started.md)
- ✅ **Proton Drive cloud backup** — opt-in backup of conversion outputs (and optionally `~/.handforge` config) via the real **proton-drive** CLI (`filesystem upload` / `create-folder`); Preferences → Cloud → Proton Drive; CLI `backup-proton`, `convert --proton-backup` / `--no-proton-backup`; status in `list-cloud`; docs in [docs/cloud.md](docs/cloud.md) + [docs/desktop.md](docs/desktop.md); no API keys stored in HandForge (uses existing CLI auth session)

## 2027 Continuity → Desktop polish

Ops/polish after E2E desktop docs: ship a polished day-to-day GUI on Linux/Windows/macOS (icons, launchers, packaging, then a versioned release).

- ✅ **System tray / window icon** — packaged multi-size PNGs under `handforge/resources/`; `handforge.util.icons.app_icon()` / `ensure_tray_icon()` set a non-null `QIcon` before `QSystemTrayIcon.show()` (fixes `QSystemTrayIcon::setVisible: No Icon set`); window + `QApplication` icon; duplicate tray removed from `handforge/app.py`; regenerate via `scripts/generate-app-icons.py`; tests in `tests/test_tray_icon.py`
- ✅ **Linux `.desktop` launcher / start-menu integration** — `packaging/linux/handforge.desktop` template; `handforge install-desktop` (or `scripts/install-desktop.sh`) writes FreeDesktop entry + hicolor icons under `~/.local/share` (optional `--system` / `--prefix`); `handforge-gui` console script for absolute `Exec=`; tests in `tests/test_desktop_linux.py`; see [docs/desktop.md](docs/desktop.md)
- ✅ **CI packaging for desktop wheels** — GitHub Actions (`.github/workflows/packaging.yml`) builds sdist+wheel, `twine check`, verifies `handforge/resources/*.png` + console entry points, uploads artifacts; tag pushes attach packages to the GitHub Release; optional PyPI Trusted Publishing (OIDC) when repo var `PYPI_TRUSTED_PUBLISHING=true`
- ✅ **Modern media desktop shell** — sidebar library chrome + Convert stage (queue | active jobs), Library hub, forge charcoal/copper theme, bundled Manrope, nav indicator + stage fade + start pulse; `handforge/ui/theme.py`, `handforge/ui/shell.py`; docs in [docs/desktop.md](docs/desktop.md)
- ⬜ **Versioned release from Unreleased** — bump past 1.3.2, fold CHANGELOG Unreleased → tagged release

## Completed Milestones

### Unreleased (Q4 2026)
- ✅ Adaptive parallel pool for large batches (optional Rust `handforge_scheduler` + Python fallback; Preferences `adaptive_parallel`)
- ✅ Progress tracking accuracy under heavy parallel load (monotonic %, speed-aware ETA, wired `ewma_alpha`, coalesced table updates, batch status aggregate)
- ✅ Comprehensive unit and integration tests (`tests/`; real FFmpeg conversion paths via lavfi-generated clips)
- ✅ Headless CLI (`python -m handforge` / `handforge`) for batch convert + list-presets via shared Orchestrator/FFmpeg stack
- ✅ Preset template library (`handforge/data/preset_templates.json`): curated Podcast/Speech/Music/Archive/Video templates; GUI Settings → Preset Template Library; CLI `list-templates` / `apply-template` / `export-presets` / `import-presets`; `--preset` resolves template ids/names
- ✅ Actionable conversion errors (`handforge/util/errors.py`): maps missing FFmpeg, disk full, permissions, missing/corrupt input, unsupported codec/muxer, filter failures, timeouts, and incomplete output to summary + “What to try” steps; wired through orchestrator, CLI, and GUI log/tooltips
- ✅ Keyboard shortcuts for common actions (`handforge/ui/main_window.py`): Ctrl+O / Ctrl+Shift+O add files/folder; Ctrl+Return start; Ctrl+. stop; Delete remove selected; Ctrl+Shift+K clear queue; Ctrl+, prefs; Ctrl+P / Ctrl+Shift+L presets; Ctrl+1/2 focus queue/active; F1 shortcuts dialog
- ✅ Hardware acceleration for video encodes (`handforge/util/hwaccel.py`): probe FFmpeg for NVENC / Quick Sync / VAAPI / VideoToolbox; Preferences + CLI `--hw-accel` / `list-hw-accel`; Auto selects a working backend and falls back to libx264/libx265 on failure
- ✅ Advanced audio filters (`handforge/util/audio_filters.py`): FFmpeg `equalizer` (3-band), `acompressor`, `alimiter`, `afftdn`; Preferences Audio tab + CLI `--eq` / `--compressor` / `--limiter` / `--denoise`; off by default
- ✅ Video filters (`handforge/util/video_filters.py`): FFmpeg `eq` (brightness / contrast / saturation) and single-pass `deshake` stabilization; Preferences Video tab + CLI `--video-color` / `--brightness` / `--contrast` / `--saturation` / `--stabilize`; off by default; CPU filters before HW upload
- ✅ Plugin system (`handforge/plugins/`): directory + `handforge.plugins` entry-point discovery; extension points for presets and pre/post-convert hooks wired into Orchestrator workers and `all_presets()`; example `examples/plugins/archive_flac_sidecar/`; CLI `list-plugins`; see [docs/plugins.md](docs/plugins.md)
- ✅ Cloud storage integration (`handforge/util/cloud.py`): local sync roots (Dropbox / Google Drive / OneDrive / Nextcloud + configured folders); optional rclone `remote:path` pick-up/save with graceful fallback when rclone is missing; Preferences → Cloud; CLI `list-cloud` / `convert --cloud-remote` / `--cloud-output`
- ✅ Optional performance analytics (`handforge/util/analytics.py`): opt-in, **local-only** per-job/batch metrics (encode speed, duration, throughput, peak parallel, ETA MAE) under `~/.handforge/analytics/`; Preferences → Advanced (default OFF); CLI `convert --analytics` / `--no-analytics`, `list-analytics`; GUI status-bar summary after batches
- ✅ Companion remote queue monitoring (`handforge/companion/`): opt-in HTTP `/api/status` + mobile web UI driven by live Orchestrator queue/active/progress; default off / localhost; shared token required for LAN (`0.0.0.0`); Preferences → Advanced → Companion; CLI `serve`, `convert --companion` / `--companion-lan`; phone browser is the mobile companion for now (store apps later)
- ✅ Shared workstation web UI (`handforge/companion/` control): `SessionController` + `/api/control` routes on the same companion server; start/stop Orchestrator, add/remove pending or queued jobs, change output dir / preset / format basics; token required for all writes; GUI + `handforge serve` wire real Orchestrator (no mock queue)
- ✅ Android / GrapheneOS companion (`companions/android/`): PWA + WebView/Capacitor scaffold, no Play Services; LAN control of Orchestrator
- ✅ Meta Quest 3 companion (`/quest.html`, `companions/quest/`): Quest Browser UI for queue monitor + shared control
- ✅ Real-time conversion preview (FFmpeg), collaborative LAN preset sharing, advanced local analytics reporting
- ✅ Watch-folder / hotfolder auto-convert (`handforge watch` + `seen_files.json`)
- ✅ Crash-safe queue persistence (`~/.handforge/queue.json`; GUI + `serve` restore)
- ✅ Companion live status via SSE (`GET /api/events`) with polling fallback
- ✅ On-device Android FFmpeg (Termux RUN_COMMAND + SAF staging + encode presets; JDK 17 companion CI)
- ✅ Quest / store HTTPS packaging: Meta Bubblewrap 2D TWA templates + `quest-https-package.sh`, Digital Asset Links route, Caddy/nginx TLS examples (`companions/quest/bubblewrap/`)
- ✅ Bundled multi-ABI Android FFmpeg: reproducible fetch script + SHA256 pins, jniLibs `libffmpeg.so` + libav* deps, LocalEncode prefers bundled when present
- ✅ On-headset heavy encodes on Quest: same Android APK (`LocalEncodeActivity`, heavy tier presets, `HandForgeNative` from `/quest.html`); Termux fallback; thermal honesty + LAN host for long jobs (`companions/quest/README.md`)
- ✅ Desktop install + usage guide for Windows / Linux / macOS (`docs/desktop.md`; canonical `.venv` + editable install; GUI and CLI post-install paths)
- ✅ Desktop polish: system tray / window icon (`handforge/resources/*.png`, `handforge/util/icons.py`; no Qt “No Icon set” on tray show)
- ✅ Desktop polish: Linux `.desktop` launcher (`handforge install-desktop`, `handforge-gui`, hicolor icons, `packaging/linux/handforge.desktop`)
- ✅ Desktop polish: CI packaging for desktop wheels (`.github/workflows/packaging.yml`; sdist/wheel + package data; artifacts; optional PyPI OIDC)
- ✅ Desktop polish: modern media desktop shell (sidebar + Convert/Library stages, forge theme, Manrope, motion)
- ✅ Proton Drive cloud backup (opt-in via real `proton-drive` CLI; Preferences → Cloud; `backup-proton` / `convert --proton-backup`; [docs/cloud.md](docs/cloud.md))

### v1.3.2 (Q4 2026)
- ✅ Permission-aware output directory handling and pre-conversion write checks
- ✅ Active Conversions context menu (play output, open folder)
- ✅ Output filename display in Active Conversions table

### v1.3.1 (Q1 2026)
- ✅ Critical video stream preservation in video-to-video conversions
- ✅ Orchestrator and progress UI bug fixes

### v1.3.0 (Q1 2026)
- ✅ macOS support (Apple Silicon and Intel)
- ✅ Multi-language support (11 languages)
- ✅ Enhanced error handling and progress bar styling

### v1.2.0 (2025)
- ✅ Preferences dialog with comprehensive settings
- ✅ Audio/video trimming and effects
- ✅ System tray integration
- ✅ Audio quality analysis

### v1.1.0 (2025)
- ✅ Video conversion support
- ✅ Smart video compression
- ✅ Two-pass encoding
- ✅ PyQt6 migration

### v1.0.0 (2025)
- ✅ Initial release
- ✅ Batch audio conversion
- ✅ Preset system
- ✅ Metadata management

---

For current issues and feature requests, see [GitHub Issues](https://github.com/VoxHash/HandForge/issues).
