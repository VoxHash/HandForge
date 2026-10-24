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
- Improved error messages with actionable solutions
- Keyboard shortcuts for common actions

## 2027

### Advanced Features
- Hardware acceleration support (NVENC, QuickSync, VAAPI)
- Advanced audio filters (EQ, compressor, limiter, noise reduction)
- Video filters (brightness, contrast, saturation, stabilization)
- Plugin system architecture for extensibility

### Platform & Integration
- Cloud storage integration (pick up / save to remote folders)
- Optional performance analytics for long batch jobs

## Future

### Platform Expansion
- Companion mobile apps (remote queue monitoring)
- Optional web-based interface for shared workstations

#### Mobile & Headset Targets
These are **not** near-term ports of the desktop PyQt6 UI. They depend on a shared conversion/queue core (and the native scheduler path) before any full client ships.

- **Android / GrapheneOS app** — Remote queue control and lightweight convert/transcode on-device where FFmpeg and storage permissions allow. GrapheneOS is called out for privacy-hardened installs (no Google Play Services assumption); expect sideload/F-Droid-style distribution first. Rationale: HandForge users already batch on desktops; a locked-down phone client covers “send this recording home” without a full desktop rewrite.
- **Meta Quest 3 app** — Queue monitoring and short media prep (trim/export) from a VR/MR headset, talking to a desktop or LAN HandForge instance. On-headset heavy encodes are a later stretch goal only. Rationale: creators already review media in Quest; a companion surface beats forcing ALT-TAB to a monitor mid-session.

### Advanced Capabilities
- Real-time preview of conversions
- Collaborative features (preset sharing)
- Advanced analytics and reporting

## Completed Milestones

### Unreleased (Q4 2026)
- ✅ Adaptive parallel pool for large batches (optional Rust `handforge_scheduler` + Python fallback; Preferences `adaptive_parallel`)
- ✅ Progress tracking accuracy under heavy parallel load (monotonic %, speed-aware ETA, wired `ewma_alpha`, coalesced table updates, batch status aggregate)
- ✅ Comprehensive unit and integration tests (`tests/`; real FFmpeg conversion paths via lavfi-generated clips)
- ✅ Headless CLI (`python -m handforge` / `handforge`) for batch convert + list-presets via shared Orchestrator/FFmpeg stack
- ✅ Preset template library (`handforge/data/preset_templates.json`): curated Podcast/Speech/Music/Archive/Video templates; GUI Settings → Preset Template Library; CLI `list-templates` / `apply-template` / `export-presets` / `import-presets`; `--preset` resolves template ids/names

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
