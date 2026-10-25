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
- **Audio**: Loudness normalization, **EQ / compressor / limiter / noise reduction**, cover art preferences
- **Video**: Default quality, codec, **hardware acceleration** (Auto / Software / NVENC / Quick Sync / VAAPI / VideoToolbox), size reduction settings
- **Cloud**: Local sync roots (Dropbox / Google Drive / OneDrive / Nextcloud), optional rclone remote
- **Advanced**: Auto-retry, progress smoothing, **optional local performance analytics** (off by default), **Companion monitor + shared workstation** (off by default)

Use **Detect Hardware Encoders…** on the Video tab to probe FFmpeg on this machine. Auto mode picks a working backend and falls back to software if encode fails.

### Companion / shared workstation (phone or another desktop browser)

1. Open **Settings** → **Preferences** → **Advanced** → **Companion**.
2. Enable the companion server (off by default). Leave host at `127.0.0.1` for this machine only.
3. For LAN shared control: set host to `0.0.0.0` (or use CLI `--lan`), keep the shared token private (auto-minted on save if empty). Control writes always need the token.
4. Open the status-bar URL (includes `?token=…`). The page uses live SSE (`/api/events`) with 1s polling fallback for queue / active progress, and exposes Start / Stop, add/remove jobs, output/preset, **real-time FFmpeg preview**, **LAN preset share**, and **advanced analytics**. Pending work survives a crash via `~/.handforge/queue.json`.
5. Or run `handforge serve` / `handforge serve --lan` for a headless controllable session.
6. **Install as PWA** from the browser, open **Quest UI** (`/quest.html`) on Meta Quest 3 Browser, or build the Android / GrapheneOS WebView APK under `companions/android/` (no Play Services). See [docs/companions.md](companions.md).

LAN note: anyone with the token can see job basenames and control encodes on this host. Prefer localhost when possible.

### Performance analytics (local only)

1. Open **Settings** → **Preferences** → **Advanced**.
2. Enable **Enable performance analytics (local only)** (off by default).
3. Run a batch as usual. When it finishes, the status bar shows a one-line summary (jobs ok, wall time, peak parallel, mean speed, throughput, ETA error).
4. History is stored only under `~/.handforge/analytics/` — nothing is uploaded. Use CLI `list-analytics` or `list-analytics --report` for aggregates; companion **Advanced analytics** loads the same report.

### Watch-folder / hotfolder

```bash
python -m handforge watch ~/Inbox -o ~/HandForge_Output -f mp3 --bitrate 192 --once
python -m handforge watch ~/Inbox --interval 5   # loop until Ctrl+C
```

New media must stay size/mtime-stable (default 1.5s) before convert. Seen paths are recorded in `~/.handforge/seen_files.json` so files are not re-queued.

On the **Audio** tab, enable advanced filters only when needed (all off by default). EQ uses three bands; compressor/limiter use FFmpeg `acompressor` / `alimiter`; noise reduction uses `afftdn`.

### Cloud storage (pick up / save)

1. Open **Settings** → **Preferences** → **Cloud**.
2. **Detect Sync Folders** or **Add Folder…** to register a Dropbox / Drive / OneDrive / Nextcloud (or any synced) path.
3. Select a root → **Use as Output Dir** (also updates Conversion → Output Directory) and/or **Use as Input Browse Start**.
4. Add media with **Add Files** / **Add Folder** — dialogs open in your cloud input root when set.
5. Convert as usual; files written into a sync folder are uploaded by the sync client.

**Optional rclone**: if `rclone` is on `PATH` (or you set the binary path), enable rclone support, pick a default remote from `rclone listremotes`, and use the CLI for `remote:path` pick-up/save (`list-cloud`, `convert --cloud-output`). Without rclone, local sync folders still work; remote paths are refused with a clear message.

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

- Select files in the queue and press **Delete**
- Or right-click and select **Remove from Queue**
- Clear the entire queue with **File → Clear Queue** (`Ctrl+Shift+K`)

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Add Files |
| `Ctrl+Shift+O` | Add Folder |
| `Ctrl+Return` | Start Conversion |
| `Ctrl+.` | Stop Conversion |
| `Delete` | Remove selected queue items (when queue is focused) |
| `Ctrl+Shift+K` | Clear Queue |
| `Ctrl+Shift+Delete` | Clear Active Conversions list |
| `Ctrl+,` | Preferences |
| `Ctrl+P` | Manage Presets |
| `Ctrl+Shift+L` | Preset Template Library |
| `Ctrl+1` | Focus Conversion Queue |
| `Ctrl+2` | Focus Active Conversions |
| `Ctrl+Q` | Quit |
| `F1` | Keyboard Shortcuts (Help) |

Open **Help → Keyboard Shortcuts** (or press `F1`) for the same list inside the app.

## Presets

### Using Presets

1. Select a preset from the dropdown
2. All conversions use the selected preset settings

### Managing Presets

1. Go to **Settings** → **Manage Presets**
2. Create, edit, or delete presets
3. Use **Import JSON** / **Export JSON** to share or back up custom presets
4. Presets are saved when you click OK

### Preset Template Library

Browse curated, purpose-built templates (Podcast, Speech, Music, Archive, Video) with real platform-aligned settings (for example Apple Podcasts AAC 128k stereo and YouTube 1080p H.264 ~8 Mbps):

1. Go to **Settings** → **Preset Template Library**
2. Filter by category and review the description / source
3. Click **Apply to My Presets** to install into your custom presets (appears in the preset dropdown)

CLI equivalents: `python -m handforge list-templates` and `apply-template` — see [cli.md](cli.md).

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

- **Settings** → **Manage Presets** → **Export JSON** / **Import JSON**
- Or CLI: `python -m handforge export-presets ./presets.json` / `import-presets ./presets.json`

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

1. Go to **Settings** → **Preferences** → **Audio**
2. Enable loudness normalization
3. Set target LUFS value
4. Default: -14.0 LUFS

### Advanced Audio Filters

1. Open **Settings** → **Preferences** → **Audio**
2. Enable **Equalizer**, **Compressor**, **Limiter**, and/or **Noise Reduction** as needed
3. Adjust gains / thresholds; leave unused filters disabled
4. Start a conversion — filters apply to audio-to-audio, video-to-audio, and video audio tracks

CLI equivalents: `--eq`, `--compressor`, `--limiter`, `--denoise` (see [CLI](cli.md)).

### Video Filters

1. Open **Settings** → **Preferences** → **Video**
2. Enable **Color Adjust** and set brightness / contrast / saturation, and/or enable **Stabilization**
3. Stabilization uses single-pass FFmpeg `deshake` (milder than multi-pass vidstab; works with HW encode because filters run on CPU before upload)
4. Start a video-to-video conversion — filters apply only when enabled (defaults leave encodes unchanged)

CLI equivalents: `--video-color`, `--brightness`, `--contrast`, `--saturation`, `--stabilize` (see [CLI](cli.md)).

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

