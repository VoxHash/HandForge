"""Collaborative preset sharing over the companion LAN API.

Shares custom preset JSON between workstations on the same network.
Uses the same ``companion_token`` gate as control writes — no cloud.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..core.presets import (
    BUILTIN_PRESETS,
    all_presets,
    load_custom_presets,
    parse_preset_file_payload,
    save_custom_presets,
)


def list_shareable_presets(*, include_builtin: bool = False) -> Dict[str, Any]:
    customs = load_custom_presets()
    payload: Dict[str, Dict[str, Any]] = dict(customs)
    if include_builtin:
        merged = dict(BUILTIN_PRESETS)
        merged.update(customs)
        payload = merged
    names = sorted(payload.keys())
    return {
        "ok": True,
        "type": "handforge-presets",
        "version": 1,
        "count": len(names),
        "names": names,
        "presets": payload,
        "custom_count": len(customs),
        "all_known": sorted(all_presets().keys()),
    }


def export_share_payload(*, include_builtin: bool = False) -> Dict[str, Any]:
    data = list_shareable_presets(include_builtin=include_builtin)
    return {
        "version": 1,
        "type": "handforge-presets",
        "presets": data["presets"],
    }


def import_share_payload(
    raw: Any,
    *,
    replace: bool = False,
    names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Import presets from a share JSON body into custom presets."""
    if not isinstance(raw, dict):
        return {"ok": False, "error": "body_must_be_object"}
    try:
        incoming = parse_preset_file_payload(raw)
    except ValueError as exc:
        return {"ok": False, "error": "invalid_presets", "detail": str(exc)}
    if not incoming:
        return {"ok": False, "error": "no_presets"}

    if names:
        wanted = {n.strip() for n in names if str(n).strip()}
        incoming = {k: v for k, v in incoming.items() if k in wanted}
        if not incoming:
            return {"ok": False, "error": "names_not_found"}

    if replace:
        customs: Dict[str, Dict[str, Any]] = {}
    else:
        customs = load_custom_presets()
    before = set(customs.keys())
    customs.update(incoming)
    save_custom_presets(customs)
    added = sorted(set(incoming.keys()) - before)
    updated = sorted(set(incoming.keys()) & before)
    return {
        "ok": True,
        "imported": sorted(incoming.keys()),
        "added": added,
        "updated": updated,
        "custom_count": len(customs),
    }
