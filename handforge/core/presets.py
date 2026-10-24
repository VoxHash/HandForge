"""Built-in presets, curated template library, and import/export for HandForge."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .settings import load_custom_presets, save_custom_presets

# Names and options mirror the GUI preset combo (without emoji prefixes).
BUILTIN_PRESETS: Dict[str, Dict[str, Any]] = {
    "MP3 192k": {"format": "mp3", "mode": "CBR", "bitrate": "192"},
    "AAC 256k": {"format": "aac", "mode": "CBR", "bitrate": "256"},
    "FLAC Lossless": {"format": "flac", "mode": "Lossless"},
    "MP4 H.264": {
        "format": "mp4",
        "mode": "CBR",
        "video_codec": "libx264",
        "video_bitrate": "5000",
        "bitrate": "192",
    },
    "MKV H.264": {
        "format": "mkv",
        "mode": "CBR",
        "video_codec": "libx264",
        "video_bitrate": "5000",
        "bitrate": "192",
    },
    "MP4 H.265 (Smart Compression)": {
        "format": "mp4",
        "mode": "CBR",
        "video_codec": "libx265",
        "reduce_size": True,
        "use_hevc": True,
        "size_reduction_factor": 7.0,
        "bitrate": "192",
    },
    "MKV H.265 (Smart Compression)": {
        "format": "mkv",
        "mode": "CBR",
        "video_codec": "libx265",
        "reduce_size": True,
        "use_hevc": True,
        "size_reduction_factor": 7.0,
        "bitrate": "192",
    },
    "WebM VP9": {
        "format": "webm",
        "mode": "CBR",
        "video_codec": "libvpx-vp9",
        "video_quality": "30",
        "bitrate": "192",
    },
    "Extract Audio (MP3)": {
        "format": "mp3",
        "mode": "CBR",
        "bitrate": "192",
        "extract_audio_only": True,
    },
}

_TEMPLATE_CACHE: Optional[Dict[str, Any]] = None


def normalize_preset_name(name: str) -> str:
    """Strip optional non-ASCII (emoji) prefix from a preset display name."""
    if " " in name:
        parts = name.split(" ", 1)
        first_part = parts[0]
        if first_part and not first_part.isascii():
            return parts[1]
    return name


def _templates_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "preset_templates.json"


def load_template_library(*, force_reload: bool = False) -> Dict[str, Any]:
    """Load the packaged preset template library JSON."""
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is not None and not force_reload:
        return _TEMPLATE_CACHE
    path = _templates_path()
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "templates" not in data:
        raise ValueError(f"Invalid preset template library: {path}")
    _TEMPLATE_CACHE = data
    return data


def list_templates(
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return curated templates, optionally filtered by category (case-insensitive)."""
    templates = list(load_template_library().get("templates", []))
    if category:
        needle = category.strip().lower()
        templates = [
            t for t in templates if str(t.get("category", "")).lower() == needle
        ]
    return [dict(t) for t in templates]


def list_template_categories() -> List[str]:
    """Return sorted unique template categories."""
    cats = {str(t.get("category", "Other")) for t in list_templates()}
    return sorted(cats)


def get_template(id_or_name: str) -> Dict[str, Any]:
    """Resolve a template by id or display name. Raises KeyError if unknown."""
    key = id_or_name.strip()
    key_lower = key.lower()
    for template in list_templates():
        if str(template.get("id", "")).lower() == key_lower:
            return dict(template)
        if str(template.get("name", "")).lower() == key_lower:
            return dict(template)
    raise KeyError(id_or_name)


def template_options(template: Dict[str, Any]) -> Dict[str, Any]:
    """Return conversion options from a template record."""
    options = template.get("options")
    if not isinstance(options, dict) or "format" not in options:
        raise ValueError(
            f"Template {template.get('id')!r} is missing a valid options block"
        )
    return dict(options)


def all_presets() -> Dict[str, Dict[str, Any]]:
    """Return built-in presets merged with user custom presets (custom wins)."""
    merged = dict(BUILTIN_PRESETS)
    merged.update(load_custom_presets())
    return merged


def get_preset(name: str) -> Dict[str, Any]:
    """Resolve a preset by name, then by template id/name. Raises KeyError if unknown."""
    name_clean = normalize_preset_name(name)
    presets = all_presets()
    if name_clean in presets:
        return dict(presets[name_clean])
    try:
        return template_options(get_template(name_clean))
    except KeyError as exc:
        raise KeyError(name_clean) from exc


def apply_template(
    id_or_name: str,
    *,
    as_name: Optional[str] = None,
    overwrite: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    """Install a library template into the user's custom presets.

    Returns ``(saved_name, options)``. Raises ``FileExistsError`` if the name
    already exists and ``overwrite`` is False.
    """
    template = get_template(id_or_name)
    options = template_options(template)
    saved_name = (as_name or str(template.get("name") or template["id"])).strip()
    if not saved_name:
        raise ValueError("Preset name cannot be empty")

    customs = load_custom_presets()
    if saved_name in customs and not overwrite:
        raise FileExistsError(
            f"Custom preset {saved_name!r} already exists "
            "(pass overwrite=True to replace)"
        )
    if saved_name in BUILTIN_PRESETS and not as_name:
        # Avoid silently shadowing a built-in unless the user chose a new name.
        saved_name = f"{saved_name} (template)"
        if saved_name in customs and not overwrite:
            raise FileExistsError(
                f"Custom preset {saved_name!r} already exists "
                "(pass overwrite=True to replace)"
            )

    customs[saved_name] = options
    save_custom_presets(customs)
    return saved_name, options


def parse_preset_file_payload(raw: Any) -> Dict[str, Dict[str, Any]]:
    """Accept either a bare name→options map or a library-style wrapper."""
    if not isinstance(raw, dict):
        raise ValueError("Preset file must be a JSON object")

    if "presets" in raw and isinstance(raw["presets"], dict):
        items = raw["presets"]
    elif "templates" in raw and isinstance(raw["templates"], list):
        items = {}
        for entry in raw["templates"]:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name") or entry.get("id")
            options = entry.get("options")
            if name and isinstance(options, dict):
                items[str(name)] = dict(options)
    else:
        items = raw

    normalized: Dict[str, Dict[str, Any]] = {}
    for name, options in items.items():
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(options, dict) or "format" not in options:
            raise ValueError(f"Preset {name!r} must be an object with a format field")
        normalized[name.strip()] = dict(options)
    return normalized


def export_presets(
    path: Union[str, Path],
    presets: Optional[Dict[str, Dict[str, Any]]] = None,
    *,
    include_builtin: bool = False,
) -> Path:
    """Write presets to a JSON file. Defaults to the user's custom presets."""
    out = Path(path).expanduser()
    if presets is None:
        data = dict(load_custom_presets())
        if include_builtin:
            merged = dict(BUILTIN_PRESETS)
            merged.update(data)
            data = merged
    else:
        data = dict(presets)

    payload = {
        "version": 1,
        "type": "handforge-presets",
        "presets": data,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return out


def import_presets(
    path: Union[str, Path],
    *,
    replace: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """Import presets from a JSON file into the user's custom presets.

    Returns the resulting custom-presets map. When ``replace`` is True, existing
    customs are discarded first; otherwise imported names overwrite on collision.
    """
    src = Path(path).expanduser()
    with open(src, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    incoming = parse_preset_file_payload(raw)
    if not incoming:
        raise ValueError(f"No presets found in {src}")

    if replace:
        customs: Dict[str, Dict[str, Any]] = {}
    else:
        customs = load_custom_presets()
    customs.update(incoming)
    save_custom_presets(customs)
    return customs


def export_template_library(path: Union[str, Path]) -> Path:
    """Copy the packaged template library JSON to ``path``."""
    out = Path(path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = load_template_library()
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return out


def known_preset_names() -> List[str]:
    """Names usable with ``get_preset`` / ``--preset`` (builtins, customs, templates)."""
    names = set(all_presets().keys())
    for template in list_templates():
        if template.get("name"):
            names.add(str(template["name"]))
        if template.get("id"):
            names.add(str(template["id"]))
    return sorted(names)
