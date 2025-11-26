# Example 2: Batch Processing with Metadata

This example shows how to process a large batch of files with metadata extraction and custom presets.

## Scenario

You have a music library with inconsistent filenames and want to:
1. Convert all files to a consistent format (AAC 256k)
2. Extract metadata from filenames
3. Add cover art automatically
4. Organize output by artist/album

## Steps

### 1. Prepare Filename Patterns

1. Go to **Settings** → **Manage Filename Patterns**
2. Add patterns like:
   - `{artist} - {title}`
   - `{track} - {artist} - {title}`
   - `{album} - {artist} - {title}`

### 2. Create Custom Preset

1. Go to **Settings** → **Manage Presets**
2. Create new preset:
   - **Name**: "AAC 256k High Quality"
   - **Format**: aac
   - **Mode**: CBR
   - **Bitrate**: 256
3. Save preset

### 3. Add Files

- Use **"Add Folder"** to add your entire music library
- Files are added recursively from subfolders

### 4. Parse Metadata

1. Select all files in queue (Ctrl+A)
2. Go to **View** → **Parse tags from filename (all)**
3. HandForge extracts artist, title, album from filenames

### 5. Fetch Cover Art

1. Select all files
2. Go to **View** → **Fetch cover from folder.jpg (selected/all)**
3. HandForge finds cover.jpg, folder.jpg, etc. in each folder

### 6. Edit Metadata (Optional)

- Double-click files to edit metadata individually
- Add missing information
- Verify cover art

### 7. Configure Conversion

- **Preset**: Select "AAC 256k High Quality"
- **Duplicates**: "Rename" to preserve all files
- **Parallel**: Increase to 4-8 for faster processing (if system allows)

### 8. Start Conversion

- Click **"Start"**
- Monitor progress in workers table
- Large batches may take time

### 9. Handle Failures

- Review failed items in workers table
- Click "🔎 log" to see error details
- Use **"Retry Failed"** or **"Retry Failed (Safe)"** to retry

### 10. Export Summary

- After completion, click **"Export Summary"**
- Save CSV with all conversion details
- Use for record-keeping

## Advanced: Custom Output Organization

While HandForge outputs to a single folder by default, you can:

1. Manually organize after conversion
2. Use the exported CSV to create scripts
3. Wait for future features (planned)

## Result

- All files converted to AAC 256k
- Metadata extracted and embedded
- Cover art added where available
- Consistent format across library

## Tips

- **Test First**: Process a small batch first
- **Backup**: Keep originals until verified
- **Monitor**: Watch for errors during large batches
- **Export**: Save summaries for reference

---

**See Also**: [Usage Guide](../usage.md) | [Configuration](../configuration.md)

