# Architecture

This document describes the architecture and design of HandForge.

## Overview

HandForge is a cross-platform audio and video converter built with:

- **PyQt6** - GUI framework
- **FFmpeg** - Audio/video processing backend
- **Python 3.9+** - Programming language

## Architecture Layers

```
┌─────────────────────────────────────┐
│         UI Layer (PyQt6)            │
│  (MainWindow, Dialogs, Widgets)     │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│      Core Layer                     │
│  (Orchestrator, Models, Settings)   │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│      Utility Layer                  │
│  (FFmpeg, File Operations)          │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│      External (FFmpeg)              │
└─────────────────────────────────────┘
```

## Core Components

### MainWindow (`ui/main_window.py`)

The main application window that provides:

- File queue management
- Workers table for progress tracking
- Menu system
- Settings dialogs
- Event handling

### Orchestrator (`core/orchestrator.py`)

Manages the conversion process:

- Worker thread pool
- Job queue
- Parallel execution control
- Signal-based communication

### Worker (`core/orchestrator.py`)

Individual conversion worker:

- Runs in QThread
- Executes FFmpeg process
- Parses progress output
- Emits progress signals

### Models (`core/models.py`)

Data structures:

- `Job` - Represents a conversion job

### Settings (`core/settings.py`)

Configuration management:

- JSON-based storage
- Settings, presets, patterns
- Auto-retry rules
- File cache

### FFmpeg Utilities (`util/ffmpeg.py`)

FFmpeg integration:

- Command building
- Process execution
- Path utilities
- Cover art handling

## Data Flow

```
User Action
    │
    ▼
MainWindow
    │
    ▼
Creates Jobs
    │
    ▼
Orchestrator.enqueue()
    │
    ▼
Worker Threads
    │
    ▼
FFmpeg Process
    │
    ▼
Progress Signals
    │
    ▼
UI Update
```

## Threading Model

HandForge uses Qt's threading model:

- **Main Thread**: UI updates and event handling
- **Worker Threads**: FFmpeg process execution
- **Signal/Slot**: Thread-safe communication

## Configuration Storage

Settings are stored in JSON files:

- Location: `~/.handforge/`
- Files:
  - `settings.json` - Application settings
  - `presets.json` - Conversion presets
  - `patterns.json` - Filename patterns
  - `autoretry.json` - Auto-retry rules
  - `seen_files.json` - Processed files cache

## Error Handling

- FFmpeg errors are captured in stderr
- Worker signals indicate success/failure
- Auto-retry system handles transient errors
- Logs are stored for debugging

## Extension Points

Future extensibility:

- Plugin system for custom codecs
- Custom metadata handlers
- Output format plugins
- Custom UI themes

## Performance Considerations

- Parallel processing for multiple files
- Thread pool management
- Memory-efficient file processing
- Progress tracking without blocking

## Dependencies

- **PyQt6**: GUI framework
- **FFmpeg**: Audio processing (external)
- **Python stdlib**: File operations, JSON, subprocess

## Design Principles

1. **Separation of Concerns**: UI, business logic, and utilities are separated
2. **Signal-Based Communication**: Qt signals for thread-safe communication
3. **Modularity**: Each component has a clear responsibility
4. **Extensibility**: Easy to add new features
5. **User Experience**: Responsive UI with real-time feedback

---

**For development**, see [Contributing](../CONTRIBUTING.md).

