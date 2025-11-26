# Example 1: Basic Audio Conversion

This example demonstrates the basic workflow of converting audio files with HandForge.

## Scenario

You have a collection of FLAC files and want to convert them to MP3 for portable devices.

## Steps

### 1. Launch HandForge

```bash
python -m handforge.app
```

### 2. Add Files

- Click **"Add Folder"** button
- Navigate to your FLAC files folder
- Select the folder
- All FLAC files are added to the queue

### 3. Select Preset

- From the preset dropdown, select **"MP3 192k"** (or create a custom preset)
- This preset converts to MP3 at 192 kbps CBR

### 4. Configure Options

- **Duplicates**: Choose "Rename" to avoid overwriting
- **Prefer External Cover**: Enable if you have folder.jpg files

### 5. Start Conversion

- Click **"Start"** button
- Watch progress in the workers table

### 6. Monitor Progress

- **Status**: Shows conversion status (Running, Done, Failed)
- **ETA**: Estimated time remaining
- **Speed**: Conversion speed multiplier
- **Progress**: Visual progress bar

### 7. Access Output

- Converted files are in `~/HandForge_Output` (or `%USERPROFILE%\HandForge_Output` on Windows)
- Files maintain original names with .mp3 extension
- Output location is shown in status bar when conversion completes

## Result

All FLAC files are converted to MP3 format at 192 kbps, ready for portable devices.

## Tips

- Use **"Export CSV"** to save a list of converted files
- Check **"Clear Finished"** to remove completed items from the table
- Use **"Retry Failed"** if any conversions fail

---

**Next**: [Example 2: Batch Processing with Metadata](example-02.md)

