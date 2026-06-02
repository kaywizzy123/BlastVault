"""
core/artist_registry.py
───────────────────────
Artist registry integration for BlastVault.

BlastVault is a *read-only consumer* of the registry.  The registry itself
is created and managed by a separate pipeline tool.

Source priority (first match wins):
  1. ``BLASTVAULT_REGISTRY`` environment variable  — set by IT via login script
  2. ``constants.REGISTRY_PATH``                   — set in Settings → Pipeline
  3. ``<ROOT_DIR>/artists.json``                   — studio root (shared by all catalogs)
  4. ``artists.json`` anywhere inside a catalog root (shallowest match wins)
  5. Local fallback: ``<app_data>/artists.json``   — works out-of-the-box

Registry file format
────────────────────
{
  "artists": [
    {
      "username":    "oogunremi",
      "name":        "Oluwakayode Ogunremi",
      "department":  "Animation",
      "role":        "Animation Supervisor",
      "permissions": "admin",
      "email":       "oo@studio.com"
    }
  ]
}

``permissions`` values
──────────────────────
  "admin"    — full access: approve/reject shots, manage sessions, settings
  "reviewer" — can approve/reject shots and add notes; cannot delete sessions
  "basic"    — submit shots and view reviews only  (default when not set)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


# ── Source resolution ─────────────────────────────────────────────────────── #

def _find_in_catalog(root: str) -> Optional[Path]:
    """Search *root* for an ``artists.json`` file.

    Checks the catalog root itself first (fast path), then searches
    recursively.  When multiple files exist the shallowest one wins;
    ties are broken alphabetically so the result is always deterministic.
    """
    root_path = Path(root)

    # Fast path — root level
    candidate = root_path / "artists.json"
    if candidate.exists():
        return candidate

    # Recursive search — sort by depth (part count) then by path string
    try:
        matches = list(root_path.rglob("artists.json"))
    except (PermissionError, OSError):
        return None

    if not matches:
        return None

    return min(matches, key=lambda p: (len(p.parts), str(p)))


def resolve_source() -> str:
    """Return the active registry source string (path or URL).

    Priority:
      1. BLASTVAULT_REGISTRY  environment variable
      2. constants.REGISTRY_PATH  (Settings → Pipeline)
      3. constants.ROOT_DIR / artists.json  (studio root — shared by all catalogs)
      4. artists.json  found anywhere inside each catalog root (shallowest wins)
      5. constants.LOCAL_REGISTRY_PATH  (local app-data fallback)
    """
    from core import constants

    env = os.environ.get("BLASTVAULT_REGISTRY", "").strip()
    if env:
        return env

    if constants.REGISTRY_PATH:
        return constants.REGISTRY_PATH

    if constants.ROOT_DIR:
        studio_candidate = Path(constants.ROOT_DIR) / "artists.json"
        if studio_candidate.exists():
            return str(studio_candidate)

    for root in constants.CATALOG_ROOTS:
        found = _find_in_catalog(root)
        if found:
            return str(found)

    return str(constants.LOCAL_REGISTRY_PATH)


def source_label() -> str:
    """Human-readable description of the active source for display in Settings."""
    from core import constants

    env = os.environ.get("BLASTVAULT_REGISTRY", "").strip()
    if env:
        return f"Environment variable  (BLASTVAULT_REGISTRY)\n{env}"

    if constants.REGISTRY_PATH:
        return f"Custom path\n{constants.REGISTRY_PATH}"

    if constants.ROOT_DIR:
        studio_candidate = Path(constants.ROOT_DIR) / "artists.json"
        if studio_candidate.exists():
            return f"Studio root\n{studio_candidate}"

    for root in constants.CATALOG_ROOTS:
        found = _find_in_catalog(root)
        if found:
            rel = found.relative_to(Path(root))
            return f"Catalog  ({Path(root).name} / {rel})\n{found}"

    return f"Local registry  (default)\n{constants.LOCAL_REGISTRY_PATH}"


# ── Registry I/O ─────────────────────────────────────────────────────────── #

def _read_registry() -> tuple[list[dict], dict]:
    """Load the registry and return ``(artists, meta)``.

    *artists* is the list of artist records.
    *meta*    is a dict of any top-level keys other than ``"artists"``
              (e.g. ``{"studio_name": "SpaceBlast Animation"}``).

    Both are empty on any read/parse error so callers can always proceed safely.
    """
    source = resolve_source()
    try:
        if source.startswith("http://") or source.startswith("https://"):
            import urllib.request
            with urllib.request.urlopen(source, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        else:
            data = json.loads(Path(source).read_text(encoding="utf-8"))
        artists = data.get("artists", [])
        meta    = {k: v for k, v in data.items() if k != "artists"}
        return artists, meta
    except Exception:
        return [], {}


def get_artist(username: str) -> Optional[dict]:
    """Return the registry record for *username*, or ``None`` if not found."""
    uname = username.lower()
    artists, _ = _read_registry()
    for artist in artists:
        if artist.get("username", "").lower() == uname:
            return artist
    return None


def list_artists() -> list[dict]:
    """Return all artist records from the active registry source."""
    artists, _ = _read_registry()
    return artists


# ── Session apply ─────────────────────────────────────────────────────────── #

def apply_registry() -> bool:
    """Read the registry once, seed the artist filter list, then apply the
    current user's identity and permissions to the running session.

    Lookup order for the current user:
      1. OS login name (``getpass.getuser()``) — matches real studio setups
         where the machine login == studio username.
      2. ``constants.CURRENT_USER`` — fallback for dev machines where the OS
         login differs from the configured studio username.

    Side-effects on ``constants``:
      * ``ARTISTS``           — registry usernames merged in (preserves existing
                                auto-discovered entries, "All" stays first).
      * ``CURRENT_USER``      — set from registry name when found.
      * ``CURRENT_DEPARTMENT``— set from registry department when found.
      * ``STATUS_LOCKED``     — False for admin, True otherwise.
      * ``REGISTRY_PERMISSION``— "admin" | "reviewer" | "basic" | "".

    Returns ``True`` if the current user was found, ``False`` otherwise.
    When ``False`` the PIN-based admin gate remains the fallback.
    """
    import getpass
    from core import constants

    all_artists, meta = _read_registry()

    # ── Studio name — registry is authoritative when present ─────────────
    registry_studio_name = meta.get("studio_name", "").strip()
    if registry_studio_name:
        constants.STUDIO_NAME = registry_studio_name

    # ── Admin PIN — registry is authoritative when present ───────────────
    # Allows the TD to set/change the PIN once in artists.json and have it
    # apply to all machines automatically.
    registry_pin_hash = meta.get("admin_pin_hash", "").strip()
    if registry_pin_hash:
        constants.ADMIN_PIN_HASH = registry_pin_hash

    # ── Seed the artist filter list ───────────────────────────────────────
    existing_set = set(constants.ARTISTS)
    for entry in all_artists:
        uname = entry.get("username", "").strip()
        if uname and uname not in existing_set:
            constants.ARTISTS.append(uname)
            existing_set.add(uname)

    # ── Find the current user ─────────────────────────────────────────────
    os_username  = getpass.getuser().lower()
    studio_name  = constants.CURRENT_USER.lower()

    artist = None
    for entry in all_artists:
        uname = entry.get("username", "").lower()
        ename = entry.get("name", "").lower()
        if uname == os_username or uname == studio_name or ename == studio_name:
            artist = entry
            break

    if artist is None:
        constants.REGISTRY_PERMISSION = ""
        if not all_artists:
            # No registry file loaded at all — solo/owner install.
            # Unlock by default so a single-person studio doesn't need a PIN
            # just to use their own app.  PIN can still be added later via the
            # lock button if they ever want to restrict access.
            constants.STATUS_LOCKED = False
        # else: registry exists but user not found — stay locked (multi-user studio)
        return False

    # ── Identity ──────────────────────────────────────────────────────────
    name = artist.get("name", "").strip()
    if name:
        constants.CURRENT_USER = name

    dept = artist.get("department", "").strip()
    if dept:
        constants.CURRENT_DEPARTMENT = dept

    # ── Permissions ───────────────────────────────────────────────────────
    perm = artist.get("permissions", "basic").lower()
    constants.REGISTRY_PERMISSION = perm

    if perm == "admin":
        constants.STATUS_LOCKED = False
    else:
        # "reviewer" and "basic" both start locked;
        # reviewer gets elevated access where the UI checks REGISTRY_PERMISSION.
        constants.STATUS_LOCKED = True

    return True
