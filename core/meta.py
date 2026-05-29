"""Metadata reader / writer for BlastVault's .meta system.

Read priority (highest → lowest)
----------------------------------
1. ``.meta`` JSON file  — publisher output, fully structured.
2. ``.txt`` sidecar     — freeform notes; any ``key: value`` lines at the top
                          are parsed as structured fallback metadata.
3. Filename parsing     — department / version extracted from the stem
                          (handled by the callers, not this module).

Layout on disk
--------------
    /shots/010/
        char_hero_v001.ma          <- asset
        char_hero_v001.txt         <- sidecar: key:value lines + free text
        .meta/
            char_hero_v001.meta    <- publisher JSON (primary)

``.meta`` schema (all fields optional)
----------------------------------------
    {
        "artist":       "johndoe",
        "department":   "Animation",
        "version":      10,
        "published_at": "2026-05-29T14:32:00",
        "dcc":          "Maya 2025",
        "notes":        "Cleaned up foot contacts"
    }

``.txt`` sidecar key:value syntax (fallback)
---------------------------------------------
    artist: johndoe
    department: Animation
    version: 10

    Free-form description text goes here after a blank line
    (or any line that does not match ``key: value``).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Sidecar keys that are treated as structured metadata when found as
# ``key: value`` lines.  Everything else becomes the description.
_SIDECAR_KEYS  = {"artist", "department", "version"}
_KV_RE         = re.compile(r"^\s*(\w+)\s*:\s*(.+)", re.IGNORECASE)

_META_DIR = ".meta"
_META_EXT = ".meta"


# ── Path helpers ──────────────────────────────────────────────────────────── #

def meta_path(asset_path: Path) -> Path:
    """Return the .meta file path that corresponds to *asset_path*."""
    return asset_path.parent / _META_DIR / (asset_path.stem + _META_EXT)


# ── Read ──────────────────────────────────────────────────────────────────── #

def read_meta(asset_path: Path) -> dict:
    """Read structured metadata for *asset_path*.

    Returns the parsed dict, or ``{}`` if no .meta file exists or it is
    malformed.
    """
    mp = meta_path(asset_path)
    if mp.exists():
        try:
            return json.loads(mp.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def read_folder_meta(folder: Path) -> dict[str, dict]:
    """Return ``{stem: meta_dict}`` for every .meta file inside *folder/.meta/*.

    Only scans the immediate .meta subfolder.  For recursively nested
    directories (e.g. SEQ folders) call ``read_meta(p)`` per file instead.
    """
    meta_dir = folder / _META_DIR
    result: dict[str, dict] = {}
    if not meta_dir.is_dir():
        return result
    for f in meta_dir.glob(f"*{_META_EXT}"):
        try:
            result[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return result


def _parse_sidecar(asset_path: Path) -> dict:
    """Parse structured fields and description from a ``.txt`` sidecar.

    Any line matching ``key: value`` where *key* is one of the recognised
    sidecar keys is extracted as structured metadata.  All remaining lines
    (including blank lines) form the ``description`` value.

    Returns ``{}`` if the sidecar does not exist or cannot be read.
    """
    sidecar = asset_path.with_suffix(".txt")
    if not sidecar.exists():
        return {}
    try:
        text = sidecar.read_text(encoding="utf-8")
    except Exception:
        return {}

    result: dict = {}
    desc_lines: list[str] = []

    for line in text.splitlines():
        m = _KV_RE.match(line)
        if m and m.group(1).lower() in _SIDECAR_KEYS:
            key = m.group(1).lower()
            val: str | int = m.group(2).strip()
            if key == "version":
                try:
                    val = int(val)          # type: ignore[assignment]
                except ValueError:
                    pass
            result[key] = val
        else:
            desc_lines.append(line)

    desc = "\n".join(desc_lines).strip()
    if desc:
        result["description"] = desc

    return result


def read_meta_with_fallback(asset_path: Path) -> dict:
    """Return structured metadata using the full fallback chain.

    Priority:
      1. ``.meta`` JSON (publisher output)
      2. ``.txt`` sidecar ``key: value`` lines
      3. ``{}``  (callers handle filename-level fallback themselves)

    The returned dict may contain a ``"description"`` key sourced from the
    sidecar; callers that need the raw description separately can still read
    the ``.txt`` file directly.
    """
    meta = read_meta(asset_path)
    if meta:
        return meta
    return _parse_sidecar(asset_path)


# ── Write ─────────────────────────────────────────────────────────────────── #

def write_meta(asset_path: Path, data: dict) -> None:
    """Write *data* as the .meta file for *asset_path*.

    Creates the .meta directory if it does not exist.
    """
    mp = meta_path(asset_path)
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
