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
  "parallel": 2
}
```

**Range**: 1-32  
**Default**: 2

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

Exponential Weighted Moving Average for ETA smoothing:

```json
{
  "ewma_alpha": 0.3
}
```

**Range**: 0.05-0.9  
**Default**: 0.3

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

### Export Settings

Settings can be exported via the UI:
- **Settings** → **Export Presets (JSON)**
- **Settings** → **Export Patterns (JSON)**

### Import Settings

Import previously exported settings:
- **Settings** → **Import Presets (JSON)**
- **Settings** → **Import Patterns (JSON)**

## Advanced Configuration

For advanced users, you can directly edit the JSON files in `~/.handforge/`. Make sure to:

1. Close HandForge before editing
2. Use valid JSON syntax
3. Back up your settings first

---

**Need help?** See [Troubleshooting](troubleshooting.md) or [FAQ](faq.md).

