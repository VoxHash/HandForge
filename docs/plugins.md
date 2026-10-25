# Plugins

HandForge ships a small, production-usable plugin system so you can add
**conversion presets** and **pre/post-convert hooks** without forking the app.

## Extension points

| Extension | Registry API | When it runs |
|-----------|--------------|--------------|
| Presets | `registry.register_preset(name, options)` | Merged into `all_presets()` / CLI `--preset` / GUI list |
| Pre-convert | `registry.register_pre_convert(hook)` | After output path is resolved, before FFmpeg starts (may mutate `ctx.job`) |
| Post-convert | `registry.register_post_convert(hook)` | After each conversion attempt (success or failure) |

Preset priority on name clash: **built-in → plugin → custom** (custom wins).

Hook failures are logged and never abort the encode.

## Discovery

Plugins are loaded at GUI and CLI startup when `plugins_enabled` is true (default).

1. **Config directory** — `~/.handforge/plugins/<name>/plugin.py`
2. **Environment** — `HANDFORGE_PLUGIN_DIRS` (path separator `:` / `;`), each entry a folder of plugin packages
3. **Settings** — `plugin_dirs`: list of extra directories in `settings.json`
4. **Entry points** — packaging group `handforge.plugins` (installable packages)

```text
~/.handforge/plugins/
  my_plugin/
    plugin.py          # must define register(registry)
```

## Writing a plugin

Minimal `plugin.py`:

```python
from handforge.plugins.api import PluginInfo

def register(registry):
    registry.register_preset(
        "My Podcast 128k",
        {"format": "mp3", "mode": "CBR", "bitrate": "128"},
    )

    def after(ctx):
        if ctx.success:
            print(f"Done: {ctx.dst}")

    registry.register_post_convert(after)
    return PluginInfo(
        name="my_plugin",
        version="1.0.0",
        description="Example podcast preset",
    )
```

`ConvertHookContext` fields: `src`, `dst`, `format`, `success`, `job`, `settings`, `message`.

### Installable package (entry points)

In the plugin package’s `pyproject.toml`:

```toml
[project.entry-points."handforge.plugins"]
my_plugin = "my_plugin_pkg.plugin:register"
```

## Example (in-repo)

[`examples/plugins/archive_flac_sidecar/`](../examples/plugins/archive_flac_sidecar/) registers:

- Preset **Archive FLAC (plugin)** (`format=flac`, lossless)
- Post-convert hook that writes `<output>.handforge.json` after successful encodes

Load it:

```bash
export HANDFORGE_PLUGIN_DIRS="$(pwd)/examples/plugins"
python -m handforge list-plugins -v
python -m handforge list-presets | grep plugin
python -m handforge convert clip.wav --preset "Archive FLAC (plugin)" -o ./out
```

## CLI

```bash
python -m handforge list-plugins
python -m handforge list-plugins -v
```

## Settings

| Key | Default | Meaning |
|-----|---------|---------|
| `plugins_enabled` | `true` | Master switch |
| `plugin_dirs` | `[]` | Extra plugin search directories |

## API surface

```python
from handforge.plugins import (
    ensure_plugins_loaded,
    get_registry,
    load_plugins,
    ConvertHookContext,
    PluginInfo,
)
```

See also [Architecture](architecture.md) and [API Reference](api.md).
