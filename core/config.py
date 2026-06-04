import json
import shutil
import fnmatch
from pathlib import Path
from . import constants


def load_config():
    if constants.CONFIG_PATH.exists():
        try:
            with constants.CONFIG_PATH.open("r") as f:
                data = json.load(f)

            constants.EXCLUDED_PATTERNS = data.get("excluded_patterns", [])
            constants.STUDIO_NAME       = data.get("studio_name",  constants.STUDIO_NAME)
            constants.CURRENT_USER      = data.get("current_user", constants.CURRENT_USER)
            constants.ROOT_DIR          = data.get("root_dir",     constants.ROOT_DIR)
            constants.DEPARTMENTS = data.get("departments", constants.DEPARTMENTS)
            # Strip any purely-numeric tokens that crept in from filename scanning
            constants.ARTISTS = [
                a for a in data.get("artists", constants.ARTISTS)
                if not str(a).isdigit()
            ]

            # "admin_pin_hash" is the current key; fall back to the old
            # "supervisor_pin_hash" key so existing configs migrate silently.
            constants.REGISTRY_PATH = data.get("registry_path", "")

            constants.ADMIN_PIN_HASH = (
                data.get("admin_pin_hash")
                or data.get("supervisor_pin_hash", "")
            )
            if "review_types" in data:
                constants.REVIEW_TYPES = data["review_types"]

            constants.CUSTOM_PLAYERS = [
                p for p in data.get("custom_players", [])
                if isinstance(p, dict) and p.get("name") and p.get("path")
            ]

            # Tools
            if "blast_player_path" in data:
                constants.BLAST_PLAYER_PATH = Path(data["blast_player_path"])

            # Window / splitter state
            geo = data.get("window_geometry", {})
            if geo:
                constants.WINDOW_MAXIMIZED = geo.get("maximized", True)
                constants.WINDOW_GEOMETRY  = (
                    geo.get("x", 0), geo.get("y", 0),
                    geo.get("width", 1280), geo.get("height", 720),
                )
            if "splitter_sizes" in data:
                constants.SPLITTER_SIZES = data["splitter_sizes"]

            catalogs = data.get("catalogs", [])
            constants.CATALOG_ROOTS = catalogs
            return catalogs
        except Exception:
            constants.EXCLUDED_PATTERNS = []
    return []


def save_config(catalog_paths=None):
    try:
        existing = {}
        if constants.CONFIG_PATH.exists():
            with constants.CONFIG_PATH.open("r") as f:
                existing = json.load(f)

        existing["excluded_patterns"] = constants.EXCLUDED_PATTERNS
        existing["studio_name"]       = constants.STUDIO_NAME
        existing["current_user"]      = constants.CURRENT_USER
        existing["root_dir"]          = constants.ROOT_DIR
        existing["departments"]       = constants.DEPARTMENTS
        existing["artists"]           = constants.ARTISTS
        existing["blast_player_path"]   = str(constants.BLAST_PLAYER_PATH)
        existing["registry_path"]  = constants.REGISTRY_PATH
        existing["admin_pin_hash"] = constants.ADMIN_PIN_HASH
        existing.pop("supervisor_pin_hash", None)   # remove legacy key
        existing["review_types"]    = constants.REVIEW_TYPES
        existing["custom_players"]  = constants.CUSTOM_PLAYERS
        # ffmpeg_path is intentionally NOT saved — it is auto-detected at
        # startup via shutil.which so it always reflects the current machine.
        existing.pop("ffmpeg_path", None)   # clean up any legacy value

        # Window geometry — only write when we have real values
        if constants.WINDOW_GEOMETRY:
            x, y, w, h = constants.WINDOW_GEOMETRY
            existing["window_geometry"] = {
                "maximized": constants.WINDOW_MAXIMIZED,
                "x": x, "y": y, "width": w, "height": h,
            }
        if constants.SPLITTER_SIZES:
            existing["splitter_sizes"] = list(constants.SPLITTER_SIZES)

        if catalog_paths is not None:
            existing["catalogs"] = catalog_paths

        with constants.CONFIG_PATH.open("w") as f:
            json.dump(existing, f, indent=2)
    except Exception:
        pass


def export_config(dest_path: str) -> bool:
    """Copy the active config file to *dest_path*. Returns True on success."""
    try:
        # Make sure an up-to-date file exists before copying
        if not constants.CONFIG_PATH.exists():
            save_config()
        shutil.copy2(str(constants.CONFIG_PATH), dest_path)
        return True
    except Exception:
        return False


def import_config(src_path: str) -> bool:
    """Replace the active config with *src_path* and reload constants.
    Returns True on success."""
    try:
        shutil.copy2(src_path, str(constants.CONFIG_PATH))
        load_config()
        return True
    except Exception:
        return False


def is_excluded(name):
    for pattern in constants.EXCLUDED_PATTERNS:
        if fnmatch.fnmatch(name.lower(), pattern.lower()):
            return True
    return False


def has_media_or_subfolders(path) -> bool:
    """Return True if *path* has at least one subfolder or one media file as a direct child.

    Passes:  pipeline folders (have sub-structure even if empty), media leaf folders.
    Fails:   childless folders with no media (stray docs, notes, etc.).

    Only direct children are scanned — no deep recursion — so it stays fast.
    """
    try:
        for entry in Path(path).iterdir():
            if entry.is_dir() and entry.name != ".meta" and not is_excluded(entry.name):
                return True
            if entry.is_file() and entry.suffix.lower() in constants.ALLOWED_EXTS:
                return True
    except (PermissionError, OSError):
        pass
    return False
