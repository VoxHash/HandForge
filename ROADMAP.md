# Roadmap — HandForge

High-level milestones and planned features for HandForge.

## Q4 2026

### Performance & Stability
- Improve progress tracking accuracy under heavy parallel load
- Memory optimization for large batch conversions
- Comprehensive unit and integration tests (CI matrix already covers import checks on Windows, Linux, and macOS)

### User Experience
- Command-line interface (CLI) for headless batch processing — see [docs/cli.md](docs/cli.md) for current scope
- Preset template library
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

### Advanced Capabilities
- Real-time preview of conversions
- Collaborative features (preset sharing)
- Advanced analytics and reporting

## Completed Milestones

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
