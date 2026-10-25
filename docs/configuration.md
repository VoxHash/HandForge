# Configuration Guide

HandForge stores its configuration in JSON files located in `~/.handforge/` (or `%USERPROFILE%\.handforge\` on Windows).

## Configuration Files

- `settings.json` - Application settings
- `presets.json` - Custom conversion presets
- `patterns.json` - Filename patterns for metadata parsing
- `autoretry.json` - Auto-retry rules
- `seen_files.json` - Cache of processed files

## Application Settings

### Parallel Encoding

Control how many files are converted simultaneously:

```json
{
  "parallel": 2,
  "adaptive_parallel": true
}
```

| Key | Description | Default |
|-----|-------------|---------|
| `parallel` | Hard ceiling for concurrent conversions | `2` |
| `adaptive_parallel` | When `true`, lower concurrency from free RAM / load (Rust native scheduler if built, else Python fallback) so other apps stay responsive | `true` |

**Range** (`parallel`): 1-32  
**Default** (`parallel`): 2

See [Installation — Native Adaptive Scheduler](installation.md#optional-native-adaptive-scheduler-rust) to build the optional Rust module.

### Dark Theme

Enable or disable dark theme:

```json
{
  "dark_theme": false
}
```

**Default**: false

### Prefer External Cover

Prefer external cover art files over embedded covers:

```json
{
  "prefer_external_cover": false
}
```

**Default**: false

### Delete Original After Conversion

Delete original file after successful conversion:

```json
{
  "delete_original": false
}
```

**Default**: false

⚠️ **Warning**: This permanently deletes the source file after successful conversion. Use with caution.

### Minimize to System Tray

Minimize application to system tray when closing window:

```json
{
  "minimize_to_tray": true
}
```

**Default**: true

### Output Directory

Default output directory for converted files:

```json
{
  "output_dir": "~/HandForge_Output"
}
```

**Default**: `~/HandForge_Output` (Linux/macOS) or `%USERPROFILE%\HandForge_Output` (Windows)

### Default Video Quality

Default video quality preset:

```json
{
  "default_video_quality": "medium"
}
```

**Options**: "low", "medium", "high", "ultra"  
**Default**: "medium"

### Default Video Codec

Default video codec for conversions:

```json
{
  "default_video_codec": "libx264"
}
```

**Options**: "libx264", "libx265", "libvpx-vp9"  
**Default**: "libx264"

### Hardware Acceleration

Prefer a hardware video encoder when converting H.264/H.265 video. HandForge probes the local FFmpeg build (and runs a short encode test) before selecting a backend.

```json
{
  "hw_accel": "auto"
}
```

| Value | Behavior |
|-------|----------|
| `auto` | Prefer NVENC → Quick Sync → VAAPI → VideoToolbox when a probed encoder works; otherwise software |
| `software` | Always use libx264 / libx265 |
| `nvenc` | NVIDIA NVENC (`h264_nvenc` / `hevc_nvenc`) |
| `qsv` | Intel Quick Sync (`h264_qsv` / `hevc_qsv`) |
| `vaapi` | VAAPI (`h264_vaapi` / `hevc_vaapi`), with device init + `hwupload` |
| `videotoolbox` | Apple VideoToolbox (macOS) |

**Default**: `auto`

If the preferred HW path is unavailable or the encode fails, workers automatically retry once with software encoders. Two-pass size reduction always uses software. Set this in **Preferences → Video → Hardware Acceleration**, or override per CLI run with `--hw-accel`. See `handforge list-hw-accel` to print detection results.

### Default Size Reduction Factor

Default size reduction factor for video compression:

```json
{
  "default_reduction_factor": 7.0
}
```

**Range**: 2.0-20.0  
**Default**: 7.0

### Default Two-Pass Encoding

Enable two-pass encoding by default:

```json
{
  "default_two_pass": false
}
```

**Default**: false

### Interface Language

Set the interface language:

```json
{
  "language": null
}
```

**Options**: 
- `null` or not set = Auto-detect from system locale
- `"en"` = English
- `"ru"` = Russian
- `"pt"` = Portuguese
- `"es"` = Spanish
- `"et"` = Estonian
- `"fr"` = French
- `"de"` = German
- `"ja"` = Japanese
- `"zh"` = Chinese
- `"ko"` = Korean
- `"id"` = Indonesian

**Default**: `null` (auto-detect)

### Duplicate Handling

What to do when output file already exists:

```json
{
  "dup_handling": "Overwrite"
}
```

**Options**: "Overwrite", "Skip", "Rename"  
**Default**: "Overwrite"

### On Existing Output

Behavior when output file exists:

```json
{
  "on_exists": "overwrite"
}
```

**Options**: "skip", "overwrite", "rename"  
**Default**: "overwrite"

### Loudness Normalization

EBU R128 loudness normalization settings:

```json
{
  "normalize_lufs": false,
  "target_lufs": -14.0
}
```

**Default**: false (disabled), -14.0 LUFS

### Advanced Audio Filters

Optional FFmpeg audio filters (Preferences → **Audio**). All disabled by default.

```json
{
  "eq_enabled": false,
  "eq_bass": 0.0,
  "eq_mid": 0.0,
  "eq_treble": 0.0,
  "compressor_enabled": false,
  "compressor_threshold": 0.125,
  "compressor_ratio": 4.0,
  "compressor_attack": 20.0,
  "compressor_release": 250.0,
  "compressor_makeup": 2.0,
  "limiter_enabled": false,
  "limiter_limit": 0.95,
  "limiter_attack": 5.0,
  "limiter_release": 50.0,
  "denoise_enabled": false,
  "denoise_nr": 12.0,
  "denoise_nf": -50.0,
  "denoise_track_noise": true
}
```

| Filter | FFmpeg | Notes |
|--------|--------|-------|
| EQ | `equalizer` | 3 bands (~100 Hz / 1 kHz / 8 kHz), gains in dB |
| Compressor | `acompressor` | Threshold is linear 0–1 (0.125 ≈ −18 dBFS) |
| Limiter | `alimiter` | Peak ceiling linear (0.95 ≈ −0.4 dBFS) |
| Denoise | `afftdn` | `nr` / `nf` in dB; optional noise-floor tracking |

Filter order in the graph: denoise → EQ → compressor → limiter → fade → loudnorm.

### Video Filters

Optional FFmpeg video filters (Preferences → **Video**). All disabled by default.

```json
{
  "video_color_enabled": false,
  "video_brightness": 0.0,
  "video_contrast": 1.0,
  "video_saturation": 1.0,
  "video_stabilize_enabled": false,
  "video_stabilize_rx": 16,
  "video_stabilize_ry": 16,
  "video_stabilize_edge": "mirror"
}
```

| Filter | FFmpeg | Notes |
|--------|--------|-------|
| Color | `eq` | Brightness (−1…1), contrast (~0…2), saturation (0…3) |
| Stabilize | `deshake` | Single-pass; `rx`/`ry` search range 0–64 (multiples of 16); edge fill mode |

Full `-vf` order in encodes: deshake → crop → eq → scale → HW upload (when applicable). Multi-pass `vidstab*` is not used (requires a separate analysis pass).

### Plugins

```json
{
  "plugins_enabled": true,
  "plugin_dirs": []
}
```

| Key | Default | Notes |
|-----|---------|-------|
| `plugins_enabled` | `true` | When false, skip directory and entry-point loading |
| `plugin_dirs` | `[]` | Extra directories scanned for `<name>/plugin.py` |

Also searched: `~/.handforge/plugins/` and `HANDFORGE_PLUGIN_DIRS`. Full guide: [plugins.md](plugins.md).

### Codec Thread Caps

Thread count per codec:

```json
{
  "codec_threads": {
    "mp3": 1,
    "aac": 1,
    "m4a": 1,
    "flac": 1,
    "wav": 1
  }
}
```

### EWMA Smoothing

Exponential Weighted Moving Average for per-worker progress percent and ETA under parallel load (Preferences → Progress Smoothing α). Lower α = smoother / less jitter; higher α = more responsive.

```json
{
  "ewma_alpha": 0.3
}
```

**Range**: 0.05-0.9  
**Default**: 0.3

ETA is also speed-aware: remaining media time ÷ FFmpeg `speed=` (falls back to remaining media time when speed is unknown).

### Auto-Retry

Automatic retry on errors:

```json
{
  "auto_retry_enabled": true,
  "auto_retry_patterns": [
    "Error while decoding",
    "Invalid data found",
    "could not find codec parameters"
  ]
}
```

## Presets

Custom conversion presets are stored in `presets.json`:

```json
{
  "MP3 192k": {
    "format": "mp3",
    "mode": "CBR",
    "bitrate": "192",
    "vbrq": "-"
  },
  "High Quality AAC": {
    "format": "aac",
    "mode": "CBR",
    "bitrate": "256",
    "vbrq": "-"
  }
}
```

### Preset Fields

- `format`: Output format (mp3, aac, m4a, flac, wav, etc.)
- `mode`: Encoding mode (CBR, VBR, Lossless)
- `bitrate`: Bitrate in kbps (for CBR)
- `vbrq`: VBR quality (0-9, or "-" for default)
- Video templates may also include `video_codec`, `video_bitrate`, `video_quality`, `reduce_size`, `use_hevc`, `size_reduction_factor`, `extract_audio_only`

### Preset Template Library

Packaged curated templates live in `handforge/data/preset_templates.json` (shipped with the app; not user-edited). Apply copies into `presets.json`:

- GUI: **Settings → Preset Template Library**
- CLI: `list-templates`, `apply-template`, `export-presets --templates`

Export/import of user presets uses a JSON envelope:

```json
{
  "version": 1,
  "type": "handforge-presets",
  "presets": {
    "My Preset": { "format": "mp3", "mode": "CBR", "bitrate": "192" }
  }
}
```

## Filename Patterns

Patterns for extracting metadata from filenames:

```json
[
  "{artist} - {title}",
  "{track} - {artist} - {title}",
  "{album} - {artist} - {title}"
]
```

### Pattern Variables

- `{artist}` - Artist name
- `{title}` - Track title
- `{album}` - Album name
- `{track}` - Track number
- `{year}` - Year

## Window State

HandForge remembers window position and size:

```json
{
  "win_geom": "...",
  "win_state": "..."
}
```

These are automatically managed by the application.

## Resetting Configuration

To reset all settings to factory defaults:

1. Open HandForge
2. Go to **Settings** → **Reset to Factory**
3. Confirm the reset
4. Restart the application

Or manually delete the `~/.handforge/` directory.

## Export/Import

### Export / Import Presets

- **Settings** → **Manage Presets** → **Export JSON** / **Import JSON**
- CLI: `python -m handforge export-presets PATH` / `import-presets PATH`

## Advanced Configuration

For advanced users, you can directly edit the JSON files in `~/.handforge/`. Make sure to:

1. Close HandForge before editing
2. Use valid JSON syntax
3. Back up your settings first

---

**Need help?** See [Troubleshooting](troubleshooting.md) or [FAQ](faq.md).

