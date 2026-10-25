"""Public types and contracts for HandForge plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol


ENTRY_POINT_GROUP = "handforge.plugins"


@dataclass
class PluginInfo:
    """Metadata returned (or inferred) when a plugin registers."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    path: Optional[str] = None
    source: str = "directory"  # directory | entry_point | module


@dataclass
class ConvertHookContext:
    """Context passed to pre/post-convert hooks.

    ``job`` is the live :class:`~handforge.core.models.Job` instance. Pre-convert
    hooks may mutate job fields before FFmpeg runs. Post-convert hooks should
    treat the job as read-only.
    """

    src: str
    dst: str
    format: str
    success: bool
    job: Any
    settings: Dict[str, Any]
    message: str = ""


PreConvertHook = Callable[[ConvertHookContext], None]
PostConvertHook = Callable[[ConvertHookContext], None]


class PluginRegistrar(Protocol):
    """Minimal surface plugins receive in ``register(registry)``."""

    def register_preset(self, name: str, options: Dict[str, Any]) -> None:
        """Register a conversion preset (same shape as built-in / custom presets)."""

    def register_pre_convert(self, hook: PreConvertHook) -> None:
        """Run before FFmpeg starts (may mutate ``ctx.job``)."""

    def register_post_convert(self, hook: PostConvertHook) -> None:
        """Run after a conversion attempt finishes (success or failure)."""


@dataclass
class LoadedPlugin:
    """Record of a successfully loaded plugin."""

    info: PluginInfo
    errors: List[str] = field(default_factory=list)
