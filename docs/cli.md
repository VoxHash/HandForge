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

List built-in presets and any custom presets from `~/.handforge/presets.json`.

```bash
python -m handforge list-presets
```

### `convert`

Convert one or more files or directories (directories are scanned recursively for audio/video).

```bash
# Preset-based
python -m handforge convert input.mp3 --preset "MP3 192k"

# Batch directory
python -m handforge convert ./music --preset "AAC 256k" --output-dir ./output

# Explicit format / bitrate (no preset)
python -m handforge convert clip.wav -f mp3 --bitrate 192 -o ./out

# Metadata overrides
python -m handforge convert input.mp3 --preset "MP3 192k" \
  --title "Song Title" --artist "Artist Name"

# Parallelism
python -m handforge convert ./batch -f flac --mode Lossless --parallel 4 --no-adaptive
```

#### Options

| Option | Description |
|--------|-------------|
| `-o`, `--output-dir` | Output directory (default: settings `output_dir` or `~/HandForge_Output`) |
| `-p`, `--preset` | Named preset (see `list-presets`) |
| `-f`, `--format` | Output format (overrides preset) |
| `--mode` | `CBR`, `VBR`, or `Lossless` |
| `--bitrate` / `--vbrq` | Audio bitrate or VBR quality |
| `--video-codec` / `--video-quality` / `--video-bitrate` | Video encode options |
| `--extract-audio` | Force audio extraction from video |
| `--parallel` | Max concurrent jobs (hard ceiling) |
| `--no-adaptive` | Disable RAM/load-aware concurrency |
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

Custom presets saved in the GUI appear in `list-presets` and work with `--preset`.

## Related

- [Usage](usage.md) — GUI workflow
- [Configuration](configuration.md) — shared settings (`parallel`, `adaptive_parallel`, …)
- [Roadmap](../ROADMAP.md)

---

**HandForge CLI** · © 2026 VoxHash Technologies
