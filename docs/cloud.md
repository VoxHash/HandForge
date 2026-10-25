# Cloud storage & Proton Drive backup

HandForge supports three real cloud workflows (no fake API keys):

1. **Local sync folders** — Dropbox, Google Drive, OneDrive, Nextcloud, or any mounted sync root. FFmpeg reads/writes locally; the sync client uploads in the background.
2. **Optional rclone** — `remote:path` pick-up/save when `rclone` is on `PATH` (stage → encode → `rclone copy`).
3. **Opt-in Proton Drive backup** — upload conversion outputs (and optionally config) with the real **proton-drive** CLI already installed on the machine.

Related: [desktop.md](desktop.md) (install), [configuration.md](configuration.md) (settings keys), [cli.md](cli.md) (commands), [troubleshooting.md](troubleshooting.md).

## Prerequisites (Proton Drive)

| Component | Role |
|-----------|------|
| `proton-drive` | Official Proton Drive CLI (`filesystem upload`, `create-folder`, `list`, `auth login`) |
| `proton-drive-desktop` (optional) | Local GUI / sync worker; HandForge detects it for status only — uploads always use `proton-drive` |

Install / update the CLI from [Proton Drive CLI downloads](https://proton.me/download/drive/cli/index.html). Authenticate once:

```bash
proton-drive auth login
proton-drive filesystem list /my-files -j
```

HandForge **never** stores Proton passwords or session tokens. Auth lives in the CLI session (and optionally proton-drive-desktop).

## Enable in Preferences (GUI)

1. **Settings → Preferences → Cloud → Proton Drive backup**
2. Check **Enable Proton Drive backup after conversion**
3. Set **Remote folder** (default `/my-files/HandForge`)
4. Optionally enable **Upload automatically after each successful batch** and **Also back up settings.json / presets.json**
5. Click **Refresh Proton Drive status** — should show authenticated when the CLI session is valid

After a successful Convert batch, the status bar shows a one-line Proton Drive result when after-convert backup is on.

## CLI

### Status

```bash
handforge list-cloud
# or
python -m handforge list-cloud
```

Includes rclone remotes, local cloud roots, and Proton Drive availability / auth / remote folder.

### Backup after convert

```bash
handforge convert ./clip.mp4 -f mp4 --proton-backup \
  --proton-folder /my-files/HandForge/Out
```

| Flag | Meaning |
|------|---------|
| `--proton-backup` | Force opt-in backup for this run |
| `--no-proton-backup` | Disable backup even if settings enable it |
| `--proton-folder` | Remote folder for this run |

When `proton_drive_backup_enabled` and `proton_drive_after_convert` are true in settings, convert backs up successful outputs without `--proton-backup`.

### Explicit backup

```bash
# Upload specific files
handforge backup-proton /path/to/out1.mp3 /path/to/out2.mp4 \
  --proton-folder /my-files/HandForge

# Upload an entire output directory (folder merge)
handforge backup-proton -d ~/HandForge_Output --proton-folder /my-files/HandForge

# Default: settings output_dir (or ~/HandForge_Output) as a folder
handforge backup-proton

# Also upload ~/.handforge/settings.json and presets.json
handforge backup-proton -d ~/HandForge_Output --include-config
```

## Settings keys

Stored in `~/.handforge/settings.json` (no credentials):

| Key | Default | Description |
|-----|---------|-------------|
| `proton_drive_backup_enabled` | `false` | Master opt-in |
| `proton_drive_remote_folder` | `/my-files/HandForge` | Remote parent path |
| `proton_drive_binary` | `""` | Override PATH lookup |
| `proton_drive_backup_config` | `false` | Also upload settings/presets JSON |
| `proton_drive_after_convert` | `true` | Auto-upload after successful batch when enabled |

## Ops notes

- Remote paths should live under `/my-files/…`. Relative paths are normalized to `/my-files/<path>`.
- HandForge creates missing remote folders with `proton-drive filesystem create-folder`.
- Uploads use `-f create-new-revision -d merge -t` (new file revision, merge folders, skip thumbnails).
- Prefer a dedicated folder such as `/my-files/HandForge` so conversion backups stay separate from other Drive content.
- If `list-cloud` says not authenticated, fix the CLI session first — HandForge cannot invent login for you.
