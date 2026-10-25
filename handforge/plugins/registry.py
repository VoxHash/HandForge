"""In-memory registry of plugin presets and convert hooks."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .api import (
    ConvertHookContext,
    LoadedPlugin,
    PluginInfo,
    PostConvertHook,
    PreConvertHook,
)


class PluginRegistry:
    """Collects contributions from discovered plugins."""

    def __init__(self) -> None:
        self._presets: Dict[str, Dict[str, Any]] = {}
        self._pre_convert: List[PreConvertHook] = []
        self._post_convert: List[PostConvertHook] = []
        self._plugins: List[LoadedPlugin] = []
        self._current_plugin: Optional[str] = None

    # -- registration (called by plugins) ---------------------------------

    def register_preset(self, name: str, options: Dict[str, Any]) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Preset name must be a non-empty string")
        if not isinstance(options, dict) or "format" not in options:
            raise ValueError(
                f"Preset {name!r} must be a dict with at least a 'format' key"
            )
        self._presets[name.strip()] = dict(options)

    def register_pre_convert(self, hook: PreConvertHook) -> None:
        if not callable(hook):
            raise TypeError("pre_convert hook must be callable")
        self._pre_convert.append(hook)

    def register_post_convert(self, hook: PostConvertHook) -> None:
        if not callable(hook):
            raise TypeError("post_convert hook must be callable")
        self._post_convert.append(hook)

    # -- loader bookkeeping -----------------------------------------------

    def begin_plugin(self, info: PluginInfo) -> None:
        self._current_plugin = info.name

    def end_plugin(self, info: PluginInfo, errors: Optional[List[str]] = None) -> None:
        self._plugins.append(LoadedPlugin(info=info, errors=list(errors or [])))
        self._current_plugin = None

    def record_failure(self, info: PluginInfo, error: str) -> None:
        self._plugins.append(LoadedPlugin(info=info, errors=[error]))
        self._current_plugin = None

    # -- queries ----------------------------------------------------------

    @property
    def presets(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._presets)

    @property
    def pre_convert_hooks(self) -> List[PreConvertHook]:
        return list(self._pre_convert)

    @property
    def post_convert_hooks(self) -> List[PostConvertHook]:
        return list(self._post_convert)

    @property
    def loaded_plugins(self) -> List[LoadedPlugin]:
        return list(self._plugins)

    def clear(self) -> None:
        """Reset all contributions (used by tests / reload)."""
        self._presets.clear()
        self._pre_convert.clear()
        self._post_convert.clear()
        self._plugins.clear()
        self._current_plugin = None

    def run_pre_convert(self, ctx: ConvertHookContext) -> List[str]:
        """Invoke pre-convert hooks; return human-readable errors (non-fatal)."""
        errors: List[str] = []
        for hook in self._pre_convert:
            try:
                hook(ctx)
            except Exception as exc:  # noqa: BLE001 — isolate plugin faults
                errors.append(f"pre_convert: {exc}")
        return errors

    def run_post_convert(self, ctx: ConvertHookContext) -> List[str]:
        """Invoke post-convert hooks; return human-readable errors (non-fatal)."""
        errors: List[str] = []
        for hook in self._post_convert:
            try:
                hook(ctx)
            except Exception as exc:  # noqa: BLE001 — isolate plugin faults
                errors.append(f"post_convert: {exc}")
        return errors


_REGISTRY: Optional[PluginRegistry] = None


def get_registry() -> PluginRegistry:
    """Return the process-wide plugin registry (created on first use)."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = PluginRegistry()
    return _REGISTRY


def reset_registry() -> PluginRegistry:
    """Replace the global registry with a fresh empty one (tests / reload)."""
    global _REGISTRY
    _REGISTRY = PluginRegistry()
    return _REGISTRY
