# Usage Guide

This guide covers all features and how to use HandForge effectively.

## Basic Workflow

1. **Add Files** - Add audio or video files to the queue
2. **Select Preset** - Choose a conversion preset (audio or video)
3. **Configure Options** - Adjust settings as needed (subtitle selection, compression, trimming, etc.)
4. **Start Conversion** - Begin processing
5. **Monitor Progress** - Watch real-time progress with ETA in progress bars
6. **Access Output** - Find converted files (location shown in status bar and notifications)

## Preferences

Access comprehensive settings via **Settings** → **Preferences**:

- **General**: Language selection, parallel processing, file handling, system tray behavior
- **Conversion**: Output directory, codec thread counts
- **Audio**: Loudness normalization, cover art preferences
- **Video**: Default quality, codec, size reduction settings
- **Advanced**: Auto-retry, performance tuning

Settings are saved automatically and persist between sessions.

### Language Selection

HandForge supports 11 languages with automatic system locale detection:

- **English** (en) - Default
- **Russian** (ru)
- **Portuguese** (pt)
- **Spanish** (es)
- **Estonian** (et)
- **French** (fr)
- **German** (de)
- **Japanese** (ja)
- **Chinese** (zh)
- **Korean** (ko)
- **Indonesian** (id)

To change the language:

1. Go to **Settings** → **Preferences**
2. In the **General** tab, find the **Language** section
3. Select your preferred language from the dropdown
4. Click **OK** to save and apply

The application will automatically reload with the new language. If you select "Auto-detect (System)", HandForge will use your system's locale setting.

## Adding Files

### Method 1: Add Files Button

1. Click **"Add Files"** button
2. Select one or more audio files
3. Files are added to the queue

### Method 2: Add Folder

1. Click **"Add Folder"** button
2. Select a folder
3. All supported audio files in the folder (and subfolders) are added

### Method 3: Drag and Drop

1. Drag audio files or folders into the HandForge window
2. Files are automatically added to the queue

### Supported Formats

HandForge supports all formats that FFmpeg can read, including:

- **Audio (Lossy)**: mp3, aac, m4a, ogg, wma, opus
- **Audio (Lossless)**: flac, wav, aiff, alac, ape, wavpack
- **Video**: mp4, mkv, avi, mov, wmv, flv, webm, m4v, 3gp, ogv, mts, m2ts, ts

## Queue Management

The queue table shows:
- **#** - Row number
- **File Name** - Name of the file to convert
- **Target Format** - Output format based on selected preset
- **Subtitle** - Per-file subtitle selection dropdown (for video files with subtitles)

### Audio/Video Editing Options

HandForge supports various editing options:

- **Audio Trimming**: Trim audio by start/end time (via advanced options)
- **Audio Effects**: Apply fade in/out effects
- **Video Trimming**: Trim video by start/end time
- **Video Cropping**: Crop video to specific region
- **Resolution Scaling**: Scale video resolution
- **Frame Rate Conversion**: Convert video frame rates
- **Quality Presets**: Choose low, medium, high, or ultra quality

These options can be configured per-file or set as defaults in Preferences.

### Subtitle Selection

For video files that contain subtitle tracks:
1. Each file in the queue has its own subtitle dropdown
2. Select "None" to exclude subtitles
3. Select a specific subtitle track to include it in the converted video
4. The app automatically detects available subtitle tracks when files are added

### Filtering Queue

Use the queue filter to show specific file types:

- **All** - Show all files
- **Lossy** - Show only lossy formats
- **Lossless** - Show only lossless formats
- **By Format** - Filter by specific format (mp3, aac, flac, mp4, mkv, etc.)

### Searching Queue

Use the search box to find files by name in the queue.

### Removing Files

- Select files in the queue and press Delete
- Or right-click and select "Remove from queue"

## Presets

### Using Presets

1. Select a preset from the dropdown
2. All conversions use the selected preset settings

### Managing Presets

1. Go to **Settings** → **Manage Presets**
2. Create, edit, or delete presets
3. Presets are saved automatically

### Preset Options

- **Format**: Output format (mp3, aac, flac, etc.)
- **Mode**: CBR, VBR, or Lossless
- **Bitrate**: For CBR mode (kbps)
- **VBR Quality**: For VBR mode (0-9)

## Conversion Options

### Duplicate Handling

Choose what happens when output file exists:

- **Overwrite** - Replace existing file
- **Skip** - Skip conversion
- **Rename** - Create new file with (1), (2), etc.

### Prefer External Cover

When enabled, HandForge will use external cover art files (folder.jpg, cover.jpg, etc.) instead of embedded covers.

### Media Filter

Filter which file types to add:

- **All audio** - All supported formats
- **Lossy only** - Only lossy formats
- **Lossless only** - Only lossless formats

## Starting Conversion

1. Ensure files are in the queue
2. Select desired preset
3. Click **"Start"** button
4. Monitor progress in the workers table

## Monitoring Progress

### Workers Table

The workers table shows:

- **ID** - Worker ID
- **File** - File being converted
- **Elapsed** - Time elapsed since conversion started
- **ETA** - Estimated time remaining until completion
- **Log** - View log button (click to see conversion logs and output path)
- **Status** - Current status (click to view error log if failed)
- **Progress** - Progress bar with percentage and ETA (red if failed)

### Status Indicators

- ⏳ **Queued** - Waiting to start
- ▶️ **Running** - Currently converting
- 🔁 **Retrying** - Retrying after error
- ✅ **Done** - Successfully completed
- ❌ **Failed** - Conversion failed (click to view error log)

**Note**: Clicking on a "Failed" status will open the error log dialog showing the full error message and conversion logs.

### Filtering Workers

Filter workers by status:

- **All** - Show all workers
- **Running** - Show active conversions
- **Failed** - Show failed conversions
- **Done** - Show completed conversions
- **Pending** - Show queued items

## Managing Conversions

### Clear Completed/Failed

To remove completed or failed conversions from the Active Conversions table:

1. Go to **File** → **Clear Active Conversions List**
2. Confirm the action
3. All completed and failed items are removed from the table

### Pause/Resume

- **Pause All** - Pause all running conversions
- **Pause Worker** - Pause individual worker (right-click)
- **Resume Worker** - Resume paused worker (right-click)

### Stop Conversions

- **Stop** - Stop all running conversions
- **Stop Worker** - Stop individual worker (right-click)

### Retry Failed

- **Retry Failed** - Retry all failed conversions
- **Retry Failed (Safe)** - Retry with safe preset (WAV, lossless)

## Metadata Management

### Editing Metadata

1. Double-click a file in the queue
2. Edit metadata (title, artist, album, year, genre)
3. Add cover art if needed
4. Click OK

### Parsing from Filename

1. Select files in queue
2. Go to **View** → **Parse tags from filename**
3. Metadata is extracted using filename patterns

### Fetching Cover Art

1. Select files in queue
2. Go to **View** → **Fetch cover from folder.jpg**
3. HandForge looks for cover.jpg, folder.jpg, etc. in the same folder

## Export/Import

### Export Queue

Export queue to CSV:

1. Click **"Export CSV"** button
2. Choose save location
3. CSV includes file paths, presets, and parsed metadata

### Export Summary

Export conversion summary:

1. Click **"Export Summary"** button
2. Choose save location
3. CSV includes all worker details and statistics

### Export/Import Presets

- **Settings** → **Export Presets (CSV/JSON)**
- **Settings** → **Import Presets (CSV/JSON)**

### Export/Import Patterns

- **Settings** → **Export Patterns (CSV/JSON)**
- **Settings** → **Import Patterns (CSV/JSON)**

## Advanced Features

### Auto-Retry

Configure automatic retry on errors:

1. Go to **Settings** → **Auto-Retry**
2. Enable/disable auto-retry
3. Add/remove error patterns
4. Export/import patterns as JSON

### Codec Thread Caps

Configure thread count per codec:

1. Go to **Settings** → **Codec Thread Caps**
2. Edit JSON mapping (codec → threads)
3. Save settings

### Loudness Normalization

Configure EBU R128 normalization:

1. Go to **Settings** → **Loudness Normalization**
2. Enable normalization
3. Set target LUFS value
4. Default: -14.0 LUFS

### EWMA Smoothing

Configure ETA smoothing:

1. Go to **Settings** → **EWMA Smoothing**
2. Set alpha value (0.05-0.9)
3. Higher values = more responsive, less smooth

## Output Location

By default, converted files are saved to:

- **Windows**: `C:\Users\<username>\HandForge_Output`
- **Linux/macOS**: `~/HandForge_Output`

You can change the output directory in **Settings** → **Preferences** → **Conversion** tab.

The output location is also displayed in the status bar when a conversion completes successfully.

## Tips and Best Practices

1. **Use Presets** - Create presets for common conversions
2. **Monitor Progress** - Watch the workers table for issues
3. **Check Logs** - Review logs for failed conversions
4. **Backup Settings** - Export presets and patterns regularly
5. **Test First** - Test with a few files before large batches
6. **Parallel Processing** - Adjust parallel count based on your system

---

**Need help?** See [Troubleshooting](troubleshooting.md) or [FAQ](faq.md).

