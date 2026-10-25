# Command-Line Interface

HandForge includes a headless CLI for scriptable batch conversion. It uses the same Orchestrator, workers, and FFmpeg command builder as the GUI — no separate encode path.

Requires FFmpeg on `PATH`. No display server is required (`QT_QPA_PLATFORM=offscreen` is set automatically when needed).

## Install / run

From a clone (or after `pip install -e .`):

```bash
# Module entry
python -m handforge --help

# Console script (after editable/install)
handforge --help
```

GUI remains: `python -m handforge.app`

## Commands

### `list-presets`

List built-in, plugin, and custom presets from `~/.handforge/presets.json`.

```bash
python -m handforge list-presets
python -m handforge list-presets --include-templates
```

### `list-plugins`

List discovered plugins (directory + entry points) and optionally their presets/hooks.

```bash
python -m handforge list-plugins
python -m handforge list-plugins -v
```

See [plugins.md](plugins.md).

### `list-templates`

Browse the curated preset template library (Podcast, Speech, Music, Archive, Video).

```bash
python -m handforge list-templates
python -m handforge list-templates --category Podcast -v
```

### `apply-template`

Install a library template into `~/.handforge/presets.json` as a custom preset.

```bash
python -m handforge apply-template podcast-aac-128
python -m handforge apply-template youtube-1080p-h264 --as "YT Upload" --overwrite
```

### `export-presets` / `import-presets`

```bash
python -m handforge export-presets ./my-presets.json
python -m handforge export-presets ./library.json --templates
python -m handforge import-presets ./my-presets.json
python -m handforge import-presets ./my-presets.json --replace
```

### `list-hw-accel`

Probe the local FFmpeg for working hardware video encoders (NVENC, Quick Sync, VAAPI, VideoToolbox).

```bash
python -m handforge list-hw-accel
python -m handforge list-hw-accel --no-probe   # compiled encoders only
```

### `list-cloud`

Show rclone availability/remotes and local cloud sync roots (detected + configured). Safe when rclone is missing — prints install guidance and still lists local roots.

```bash
python -m handforge list-cloud
```

### `list-analytics`

Show whether local performance analytics is enabled and print recent batch summaries from `~/.handforge/analytics/batches.jsonl`. Nothing is uploaded.

```bash
python -m handforge list-analytics
python -m handforge list-analytics --limit 10 -v
```

### `convert`

Convert one or more files or directories (directories are scanned recursively for audio/video).

```bash
# Preset-based (built-in, custom, or template id/name)
python -m handforge convert input.mp3 --preset "MP3 192k"
python -m handforge convert episode.wav --preset podcast-aac-128 -o ./out

# Batch directory
python -m handforge convert ./music --preset "AAC 256k" --output-dir ./output

# Explicit format / bitrate (no preset)
python -m handforge convert clip.wav -f mp3 --bitrate 192 -o ./out

# Video with hardware acceleration (auto falls back to software)
python -m handforge convert clip.mkv -f mp4 --hw-accel auto -o ./out
python -m handforge convert clip.mkv -f mp4 --hw-accel nvenc -o ./out
python -m handforge convert clip.mkv -f mp4 --hw-accel software -o ./out

# Advanced audio filters (EQ / compressor / limiter / denoise)
python -m handforge convert podcast.wav -f mp3 --bitrate 192 \
  --eq --eq-bass=2 --eq-treble=-1 --compressor --limiter --denoise -o ./out

# Video color + single-pass stabilize
python -m handforge convert clip.mkv -f mp4 \
  --brightness 0.05 --contrast 1.1 --saturation 0.95 --stabilize -o ./out

# Metadata overrides
python -m handforge convert input.mp3 --preset "MP3 192k" \
  --title "Song Title" --artist "Artist Name"

# Parallelism
python -m handforge convert ./batch -f flac --mode Lossless --parallel 4 --no-adaptive

# Local performance analytics for this batch (opt-in; stored under ~/.handforge/analytics/)
python -m handforge convert ./batch -f mp3 --bitrate 192 --analytics

# Local cloud sync folder (Dropbox / Drive / OneDrive / …)
python -m handforge convert ~/Dropbox/Inbox -f mp3 --bitrate 192 -o ~/Dropbox/HandForge_Out

# rclone remote:path (requires rclone on PATH; stages locally then uploads)
python -m handforge convert gdrive:Media/In -f mp3 --bitrate 192 --cloud-output gdrive:Media/Out
python -m handforge convert ./local -f flac --cloud-remote gdrive --cloud-output gdrive:Archive
```

#### Options

| Option | Description |
|--------|-------------|
| `-o`, `--output-dir` | Output directory (default: settings `output_dir` or `~/HandForge_Output`); may be a local sync path or `remote:path` |
| `--cloud-remote` | Default rclone remote name for this run |
| `--cloud-output` | rclone `remote:path` for outputs (local stage → `rclone copy`) |
| `--no-rclone` | Disable `remote:path` handling for this run |
| `-p`, `--preset` | Named preset or template id/name (see `list-presets` / `list-templates`) |
| `-f`, `--format` | Output format (overrides preset) |
| `--mode` | `CBR`, `VBR`, or `Lossless` |
| `--bitrate` / `--vbrq` | Audio bitrate or VBR quality |
| `--video-codec` / `--video-quality` / `--video-bitrate` | Video encode options |
| `--hw-accel` | `auto`, `software`, `nvenc`, `qsv`, `vaapi`, or `videotoolbox` (default from settings) |
| `--extract-audio` | Force audio extraction from video |
| `--eq` / `--eq-bass` / `--eq-mid` / `--eq-treble` | 3-band EQ (`equalizer`); gains in dB |
| `--compressor` / `--compressor-threshold` / `--compressor-ratio` | Dynamics compressor (`acompressor`) |
| `--limiter` / `--limiter-limit` | Peak limiter (`alimiter`) |
| `--denoise` / `--denoise-nr` / `--denoise-nf` | FFT noise reduction (`afftdn`) |
| `--video-color` / `--brightness` / `--contrast` / `--saturation` | Video color via `eq` (brightness −1…1; contrast ~0…2; saturation 0…3) |
| `--stabilize` / `--stabilize-rx` / `--stabilize-ry` | Single-pass stabilization (`deshake`; rx/ry snapped to multiples of 16) |
| `--parallel` | Max concurrent jobs (hard ceiling) |
| `--no-adaptive` | Disable RAM/load-aware concurrency |
| `--analytics` | Enable local performance analytics for this run (summary on stderr after batch) |
| `--no-analytics` | Disable analytics for this run (overrides Preferences) |
| `--on-exists` | `overwrite`, `skip`, or `rename` |
| `--title` / `--artist` / `--album` / `--year` / `--genre` / `--track` | Metadata |
| `-q`, `--quiet` | Print only output paths on stdout; errors on stderr |
| `-v`, `--verbose` | Include FFmpeg log lines on stderr |

## Progress and exit codes

- Progress and status lines go to **stderr** (safe for piping paths from stdout).
- Successful output paths are printed on **stdout** (one per completed file).
- Exit codes:
  - `0` — all conversions succeeded
  - `1` — one or more conversions failed (or FFmpeg missing)
  - `2` — usage / no inputs / unknown preset / missing path

Example scripting:

```bash
python -m handforge convert ./inbox --preset "MP3 192k" -o ./out -q
echo $?
```

## Built-in presets

| Preset | Notes |
|--------|--------|
| MP3 192k | CBR MP3 192 kbps |
| AAC 256k | CBR AAC 256 kbps |
| FLAC Lossless | Lossless FLAC |
| MP4 H.264 / MKV H.264 | H.264 video |
| MP4 H.265 (Smart Compression) / MKV H.265 (Smart Compression) | HEVC size reduction |
| WebM VP9 | VP9 |
| Extract Audio (MP3) | Audio-only from video |

Custom presets saved in the GUI appear in `list-presets` and work with `--preset`. Template ids/names from `list-templates` also work with `--preset` without installing.

## Related

- [Usage](usage.md) — GUI workflow
- [Configuration](configuration.md) — shared settings (`parallel`, `adaptive_parallel`, …)
- [Roadmap](../ROADMAP.md)

---

**HandForge CLI** · © 2026 VoxHash Technologies
