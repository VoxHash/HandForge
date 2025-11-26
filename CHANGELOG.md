# Changelog

All notable changes to HandForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- Built with PyQt5 for cross-platform GUI
- FFmpeg integration for audio processing
- JSON-based settings and presets storage
- Modular architecture with core, ui, dialogs, and util modules

---

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

## [1.3.0] - 2025-01-XX

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

## [Unreleased]

### Planned
- Command-line interface
- Hardware acceleration support
- Advanced audio filters (EQ, compressor, limiter)
- Video filters (brightness, contrast, saturation)

