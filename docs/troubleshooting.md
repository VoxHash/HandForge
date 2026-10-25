# Troubleshooting Guide

Common issues and solutions when using HandForge.

## Installation Issues

### FFmpeg Not Found

**Problem**: HandForge can't find FFmpeg.

**Solutions**:
1. Verify FFmpeg is installed: `ffmpeg -version`
2. Ensure FFmpeg is in your system PATH
3. Restart terminal/command prompt after installing FFmpeg
4. On Windows, restart the computer if PATH changes don't take effect
5. On macOS, ensure Homebrew paths are in PATH: `echo $PATH | grep -q /opt/homebrew/bin || export PATH="/opt/homebrew/bin:$PATH"`

### PyQt6 Installation Fails

**Problem**: Can't install PyQt6.

**Solutions**:
```bash
# Upgrade pip first
pip install --upgrade pip

# Try installing PyQt6
pip install PyQt6

# If still failing, try:
pip install --upgrade setuptools wheel
pip install PyQt6
```

### Python Version Issues

**Problem**: HandForge requires Python 3.9+.

**Solutions**:
1. Check Python version: `python --version`
2. Install Python 3.9 or higher
3. Use `python3` instead of `python` on Linux/macOS

## Runtime Issues

### Application Won't Start

**Problem**: HandForge doesn't launch.

**Solutions**:
1. Check for error messages in terminal
2. Verify all dependencies: `pip list | grep PyQt6`
3. Try running: `python -m handforge.app`
4. Check Python version compatibility

### No Files in Queue

**Problem**: Files aren't added to queue.

**Solutions**:
1. Check file format is supported
2. Verify Media Filter setting (All audio, Lossy only, Lossless only)
3. Check if files are already in queue (duplicates are skipped)
4. Try adding files individually

### Conversions Fail

**Problem**: All or some conversions fail.

HandForge maps common failures to an actionable summary plus **What to try** steps. In the GUI, click **Status** or **View Log** on a failed row (tooltip also shows the full guidance). In the CLI, FAIL lines print the same multi-line help on stderr.

**Solutions**:
1. Read the on-screen / CLI **What to try** list first — it targets the detected cause (FFmpeg missing, disk full, permissions, corrupt input, unsupported codec, …)
2. Check FFmpeg is working: `ffmpeg -version`
3. Verify input files are valid media (`ffprobe -show_streams file`)
4. Check output directory permissions and free disk space
5. Review the full FFmpeg log in the conversion log dialog
6. Try a simpler preset (WAV / MP3 / H.264 MP4) or "Retry Failed (Safe)"

### Slow Conversions

**Problem**: Conversions are very slow.

**Solutions**:
1. Increase parallel count (Settings → adjust parallel encodes)
2. Check system resources (CPU, RAM, disk I/O)
3. Reduce parallel count if system is overloaded
4. Close other applications
5. Check if antivirus is scanning files

### Progress Not Updating

**Problem**: Progress bar/ETA not updating.

**Solutions**:
1. Check if conversion is actually running
2. Verify FFmpeg output is being parsed correctly
3. Try pausing and resuming
4. Check workers table for status

## Cloud Storage / rclone

### rclone Not Found

**Problem**: `list-cloud` says rclone is missing, or convert fails on `remote:path`.

**Solutions**:
1. Install rclone from https://rclone.org/install/ and ensure it is on `PATH` (`rclone version`)
2. Or set Preferences → Cloud → **rclone binary** to the full path
3. Or skip rclone and use a **local sync folder** (Dropbox / Google Drive / OneDrive / Nextcloud) as input/output — no rclone required
4. Use `--no-rclone` only when you intend local paths only

### No Remotes Listed

**Problem**: rclone is installed but `list-cloud` shows no remotes.

**Solutions**:
1. Run `rclone config` and create at least one remote
2. Confirm `rclone listremotes` prints names ending in `:`
3. Click **Refresh remotes** in Preferences → Cloud

### Sync Folder Not Detected

**Problem**: Detect Sync Folders finds nothing.

**Solutions**:
1. Confirm the client folder exists (e.g. `~/Dropbox`, `~/OneDrive`, macOS `~/Library/CloudStorage/…`)
2. Use **Add Folder…** to point at your synced directory manually
3. Set `cloud_roots` in `~/.handforge/settings.json`

### Upload After Convert Failed

**Problem**: Encode succeeded but rclone upload failed.

**Solutions**:
1. Check network and remote credentials (`rclone lsd remote:`)
2. Re-run upload manually: `rclone copy /path/to/local/out remote:path`
3. Prefer writing directly to a mounted sync folder if rclone auth is unreliable

## Proton Drive backup

### proton-drive Not Found

**Problem**: `list-cloud` says proton-drive is missing, or backup fails.

**Solutions**:
1. Install Proton Drive CLI from https://proton.me/download/drive/cli/index.html and ensure `proton-drive` is on `PATH`
2. Or set Preferences → Cloud → **proton-drive binary** to the full path
3. Confirm with `proton-drive version` and `handforge list-cloud`

### Not Authenticated

**Problem**: CLI found but status says not authenticated / upload fails with auth error.

**Solutions**:
1. Run `proton-drive auth login` and complete the browser / device flow
2. Verify `proton-drive filesystem list /my-files -j` returns JSON
3. Optional: keep `proton-drive-desktop` running for day-to-day sync UI (uploads still use the CLI)

### Backup Failed After Convert

**Problem**: Encode succeeded but Proton Drive backup failed.

**Solutions**:
1. Re-run `handforge backup-proton <output files…> --proton-folder /my-files/HandForge`
2. Ensure the remote parent exists or let HandForge create it under `/my-files/…`
3. Check network / Proton service status; retry once

## Performance Analytics

### No Analytics Summary After a Batch

**Problem**: Batch finishes but no analytics line appears.

**Solutions**:
1. Enable **Preferences → Advanced → Enable performance analytics (local only)** (default is off)
2. Or pass `convert --analytics` for a one-off CLI run
3. Confirm `~/.handforge/analytics/batches.jsonl` is writable
4. Run `python -m handforge list-analytics` to inspect stored history

### Privacy / Uploads

**Problem**: Concern that analytics leave the machine.

**Solutions**:
1. Analytics are **local only** — HandForge does not upload them
2. Keep the Preferences toggle off (default) if you do not want local history
3. Delete `~/.handforge/analytics/` to clear stored batches

## Companion Remote Monitor / Shared Workstation

### Phone Cannot Reach Companion

**Problem**: Phone browser fails to load the companion URL.

**Solutions**:
1. Enable Companion in Preferences (or run `handforge serve` / `convert --companion`)
2. For Wi‑Fi phones, bind `0.0.0.0` / use `--lan` and open the printed LAN IP URL (not `127.0.0.1` on the phone)
3. Include `?token=…` from the desktop status bar / CLI output
4. Confirm desktop firewall allows inbound TCP on the companion port
5. Stay on the same LAN; do not port-forward to the public internet

### Unauthorized (401)

**Problem**: Companion page or `/api/status` returns unauthorized.

**Solutions**:
1. Copy the full URL including `?token=`
2. Regenerate the token in Preferences if it changed
3. Localhost binds may omit a token for status reads; LAN binds always require one

### Control actions return 403 write_token_required

**Problem**: Start / Stop / Add jobs fail with `write_token_required`.

**Solutions**:
1. Set **Companion → Token** in Preferences (or `--token` / let `serve` mint one)
2. Reload the page using the URL that includes `?token=…`
3. Status monitoring can work without a token on localhost; **mutating control never does**

### Add jobs skips files

**Problem**: Paths added from the web UI are skipped.

**Solutions**:
1. Paths must exist as files **on the HandForge host** (not on the phone)
2. Use absolute paths to supported audio/video extensions
3. Duplicates already in pending are skipped

## Configuration Issues

### Settings Not Saving

**Problem**: Settings don't persist between sessions.

**Solutions**:
1. Check `~/.handforge/` directory exists and is writable
2. Verify permissions on settings files
3. Check disk space
4. Try resetting to factory defaults

### Presets Lost

**Problem**: Custom presets disappear.

**Solutions**:
1. Export presets regularly (Settings → Export Presets)
2. Check `~/.handforge/presets.json` exists
3. Restore from backup if available
4. Recreate presets

## UI Issues

### Window Too Small/Large

**Problem**: Window size is inconvenient.

**Solutions**:
1. Resize window manually
2. Window size is saved automatically
3. Reset window state in settings if needed

### Dark Theme Not Working

**Problem**: Dark theme doesn't apply.

**Solutions**:
1. Go to View → Dark Theme
2. Restart application
3. Check if system theme conflicts

### Buttons Not Responding

**Problem**: UI buttons don't work.

**Solutions**:
1. Check if conversion is in progress (may be disabled)
2. Restart application
3. Check for error messages
4. Verify PyQt6 installation

## File Issues

### Output Files Missing

**Problem**: Converted files not found.

**Solutions**:
1. Check default output: `~/HandForge_Output` (or `%USERPROFILE%\HandForge_Output` on Windows)
2. Verify conversion completed successfully
3. Check disk space
4. Verify file permissions

### Metadata Not Preserved

**Problem**: Metadata is lost during conversion.

**Solutions**:
1. Check if source files have metadata
2. Verify preset settings
3. Use metadata editor to add manually
4. Check FFmpeg version (older versions may have issues)

### Cover Art Missing

**Problem**: Cover art not embedded.

**Solutions**:
1. Enable "Prefer external cover" if you have folder.jpg
2. Add cover art manually via metadata editor
3. Verify source files have embedded covers
4. Check format supports cover art (mp3, aac, m4a, flac)

## Performance Issues

### High CPU Usage

**Problem**: HandForge uses too much CPU.

**Solutions**:
1. Reduce parallel count
2. Close other applications
3. Check for stuck processes
4. Restart application

### High Memory Usage

**Problem**: HandForge uses too much RAM.

**Solutions**:
1. Reduce parallel count
2. Process smaller batches
3. Clear finished items from table
4. Restart application periodically

## Getting More Help

If you're still experiencing issues:

1. Check [FAQ](faq.md) for common questions
2. Review error logs in workers table
3. Search [GitHub Issues](https://github.com/VoxHash/HandForge/issues)
4. Create a new issue with:
   - HandForge version
   - OS and version
   - Python version
   - FFmpeg version
   - Steps to reproduce
   - Error messages/logs

---

**Still need help?** See [Support](../SUPPORT.md).

