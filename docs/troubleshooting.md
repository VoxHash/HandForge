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

**Solutions**:
1. Check FFmpeg is working: `ffmpeg -version`
2. Verify input files are valid audio files
3. Check output directory permissions
4. Review error logs (click "🔎 log" on failed items)
5. Try "Retry Failed (Safe)" with WAV format
6. Check disk space

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

