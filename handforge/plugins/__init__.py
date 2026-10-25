"""HandForge plugin system — discovery, registry, and extension hooks.

Extension points (v1):

* **presets** — ``registry.register_preset(name, options)``
* **pre_convert** — ``registry.register_pre_convert(hook)`` (may mutate job)
* **post_convert** — ``registry.register_post_convert(hook)`` (after encode)

Discovery:

* Directory: ``~/.handforge/plugins/<name>/plugin.py`` and
  ``HANDFORGE_PLUGIN_DIRS`` / settings ``plugin_dirs``
* Entry points: group ``handforge.plugins``
"""

from .api import (
    ENTRY_POINT_GROUP,
    ConvertHookContext,
    LoadedPlugin,
    PluginInfo,
    PostConvertHook,
    PreConvertHook,
)
from .loader import (
    default_plugin_dirs,
    ensure_plugins_loaded,
    load_file_plugin,
    load_plugins,
    mark_plugins_unloaded,
    plugins_already_loaded,
)
from .registry import PluginRegistry, get_registry, reset_registry

__all__ = [
    "ENTRY_POINT_GROUP",
    "ConvertHookContext",
    "LoadedPlugin",
    "PluginInfo",
    "PluginRegistry",
    "PostConvertHook",
    "PreConvertHook",
    "default_plugin_dirs",
    "ensure_plugins_loaded",
    "get_registry",
    "load_file_plugin",
    "load_plugins",
    "mark_plugins_unloaded",
    "plugins_already_loaded",
    "reset_registry",
]
