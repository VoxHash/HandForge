"""Discover and load HandForge plugins from directories and entry points."""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from .api import ENTRY_POINT_GROUP, PluginInfo
from .registry import PluginRegistry, get_registry, reset_registry

logger = logging.getLogger(__name__)

_LOADED = False


def default_plugin_dirs() -> List[Path]:
    """Built-in search paths: ``~/.handforge/plugins`` (+ ``HANDFORGE_PLUGIN_DIRS``)."""
    dirs: List[Path] = []
    try:
        from ..core.settings import get_config_dir

        dirs.append(get_config_dir() / "plugins")
    except Exception:  # noqa: BLE001
        dirs.append(Path.home() / ".handforge" / "plugins")

    env = os.environ.get("HANDFORGE_PLUGIN_DIRS", "").strip()
    if env:
        for part in env.split(os.pathsep):
            part = part.strip()
            if part:
                dirs.append(Path(part).expanduser())
    return dirs


def _iter_entry_points(group: str):
    """Yield entry points for ``group`` (importlib.metadata, Py3.9+ compatible)."""
    try:
        from importlib.metadata import entry_points
    except ImportError:  # pragma: no cover
        return []

    eps = entry_points()
    if hasattr(eps, "select"):
        return list(eps.select(group=group))
    # Python 3.9 dict-like API
    return list(eps.get(group, []))  # type: ignore[call-overload]


def _call_register(module: Any, registry: PluginRegistry, info: PluginInfo) -> None:
    register = getattr(module, "register", None)
    if register is None:
        raise AttributeError(
            f"Plugin {info.name!r} has no register(registry) function"
        )
    registry.begin_plugin(info)
    result = register(registry)
    if isinstance(result, PluginInfo):
        info.name = result.name or info.name
        info.version = result.version or info.version
        info.description = result.description or info.description
    elif isinstance(result, dict):
        info.name = str(result.get("name") or info.name)
        info.version = str(result.get("version") or info.version)
        info.description = str(result.get("description") or info.description)
    registry.end_plugin(info)


def load_module_plugin(
    module: Any,
    registry: PluginRegistry,
    *,
    name: Optional[str] = None,
    path: Optional[str] = None,
    source: str = "module",
) -> PluginInfo:
    """Load an already-imported module that exposes ``register(registry)``."""
    info = PluginInfo(
        name=name or getattr(module, "__name__", "unnamed"),
        path=path,
        source=source,
    )
    try:
        _call_register(module, registry, info)
    except Exception as exc:  # noqa: BLE001
        registry.record_failure(info, str(exc))
        logger.warning("Failed to register plugin %s: %s", info.name, exc)
    return info


def load_file_plugin(
    path: Path,
    registry: PluginRegistry,
    *,
    source: str = "directory",
) -> PluginInfo:
    """Import a ``plugin.py`` (or other .py) file and call ``register``."""
    path = path.resolve()
    mod_name = f"handforge_plugin_{path.stem}_{abs(hash(str(path))) & 0xFFFF:x}"
    info = PluginInfo(name=path.parent.name if path.name == "plugin.py" else path.stem,
                      path=str(path), source=source)
    try:
        spec = importlib.util.spec_from_file_location(mod_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load plugin from {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)
        _call_register(module, registry, info)
    except Exception as exc:  # noqa: BLE001
        registry.record_failure(info, str(exc))
        logger.warning("Failed to load plugin %s: %s", path, exc)
    return info


def discover_plugin_files(directories: Sequence[Union[str, Path]]) -> List[Path]:
    """Find ``plugin.py`` files under each directory (one level of subdirs)."""
    found: List[Path] = []
    seen = set()
    for raw in directories:
        root = Path(raw).expanduser()
        if not root.is_dir():
            continue
        # Direct plugin.py in the root
        direct = root / "plugin.py"
        if direct.is_file():
            key = str(direct.resolve())
            if key not in seen:
                seen.add(key)
                found.append(direct)
        # Subdirectories: <root>/<name>/plugin.py
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name.startswith((".", "_")):
                continue
            candidate = child / "plugin.py"
            if candidate.is_file():
                key = str(candidate.resolve())
                if key not in seen:
                    seen.add(key)
                    found.append(candidate)
    return found


def load_entry_point_plugins(registry: PluginRegistry) -> List[PluginInfo]:
    """Load plugins advertised under the ``handforge.plugins`` entry-point group."""
    loaded: List[PluginInfo] = []
    for ep in _iter_entry_points(ENTRY_POINT_GROUP):
        info = PluginInfo(name=ep.name, source="entry_point")
        try:
            obj = ep.load()
            if callable(obj) and not hasattr(obj, "register"):
                # Entry point points at register() directly
                registry.begin_plugin(info)
                result = obj(registry)
                if isinstance(result, PluginInfo):
                    info = result
                    info.source = "entry_point"
                elif isinstance(result, dict):
                    info.name = str(result.get("name") or info.name)
                    info.version = str(result.get("version") or info.version)
                    info.description = str(
                        result.get("description") or info.description
                    )
                registry.end_plugin(info)
            else:
                load_module_plugin(
                    obj, registry, name=ep.name, source="entry_point"
                )
        except Exception as exc:  # noqa: BLE001
            registry.record_failure(info, str(exc))
            logger.warning("Failed entry-point plugin %s: %s", ep.name, exc)
        loaded.append(info)
    return loaded


def load_plugins(
    *,
    directories: Optional[Sequence[Union[str, Path]]] = None,
    include_entry_points: bool = True,
    enabled: bool = True,
    extra_dirs: Optional[Sequence[Union[str, Path]]] = None,
    registry: Optional[PluginRegistry] = None,
    reload: bool = False,
) -> PluginRegistry:
    """Discover and register plugins into ``registry`` (default: global).

    When ``reload`` is True the global registry is reset first.
    """
    global _LOADED
    if reload:
        reg = reset_registry() if registry is None else registry
        if registry is not None:
            registry.clear()
            reg = registry
        _LOADED = False
    else:
        reg = registry or get_registry()

    if not enabled:
        _LOADED = True
        return reg

    dirs: List[Union[str, Path]] = []
    if directories is None:
        dirs.extend(default_plugin_dirs())
    else:
        dirs.extend(directories)
    if extra_dirs:
        dirs.extend(extra_dirs)

    for path in discover_plugin_files(dirs):
        load_file_plugin(path, reg)

    if include_entry_points:
        load_entry_point_plugins(reg)

    _LOADED = True
    return reg


def ensure_plugins_loaded(
    settings: Optional[Dict[str, Any]] = None,
    *,
    reload: bool = False,
) -> PluginRegistry:
    """Idempotent load using application settings (safe to call from GUI/CLI)."""
    global _LOADED
    if _LOADED and not reload:
        return get_registry()

    enabled = True
    extra: List[str] = []
    if settings:
        enabled = bool(settings.get("plugins_enabled", True))
        raw = settings.get("plugin_dirs") or []
        if isinstance(raw, (list, tuple)):
            extra = [str(p) for p in raw]
        elif isinstance(raw, str) and raw.strip():
            extra = [raw.strip()]

    return load_plugins(
        enabled=enabled,
        extra_dirs=extra,
        reload=reload,
    )


def plugins_already_loaded() -> bool:
    return _LOADED


def mark_plugins_unloaded() -> None:
    """Test helper: allow ``ensure_plugins_loaded`` to run again."""
    global _LOADED
    _LOADED = False
