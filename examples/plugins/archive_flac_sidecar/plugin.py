"""Example HandForge plugin: Archive FLAC preset + post-convert sidecar.

Drop this directory under ``~/.handforge/plugins/`` or point
``HANDFORGE_PLUGIN_DIRS`` / Preferences ``plugin_dirs`` at
``examples/plugins``.

Demonstrates two extension points:

1. ``register_preset`` — adds **Archive FLAC (plugin)** usable with
   ``--preset`` / the GUI preset list.
2. ``register_post_convert`` — after a successful encode, writes
   ``<output>.handforge.json`` with src/dst/format metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from handforge.plugins.api import ConvertHookContext, PluginRegistrar
    from handforge.plugins.api import PluginInfo as PluginInfoType


def register(registry: "PluginRegistrar") -> "PluginInfoType":
    from handforge.plugins.api import PluginInfo

    registry.register_preset(
        "Archive FLAC (plugin)",
        {
            "format": "flac",
            "mode": "Lossless",
        },
    )
    registry.register_post_convert(_write_sidecar)

    return PluginInfo(
        name="archive_flac_sidecar",
        version="1.0.0",
        description=(
            "Example: Archive FLAC preset plus .handforge.json sidecar "
            "after successful converts"
        ),
    )


def _write_sidecar(ctx: "ConvertHookContext") -> None:
    if not ctx.success or not ctx.dst:
        return
    out = Path(ctx.dst)
    if not out.is_file():
        return
    sidecar = out.with_suffix(out.suffix + ".handforge.json")
    payload = {
        "handforge_plugin": "archive_flac_sidecar",
        "src": ctx.src,
        "dst": ctx.dst,
        "format": ctx.format,
        "message": ctx.message,
    }
    sidecar.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
