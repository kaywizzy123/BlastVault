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
            constants.ROOT_DIR          = data.get("root_dir",     constants.ROOT_DIR)
            constants.DEPARTMENTS       = data.get("departments",  constants.DEPARTMENTS)
            constants.ARTISTS           = data.get("artists",      constants.ARTISTS)

            # Tools — only override if the key is present so platform defaults
            # are kept on first run
            if "ffmpeg_path" in data:
                constants.FFMPEG_PATH = data["ffmpeg_path"]
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

            return data.get("catalogs", [])
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
        existing["root_dir"]          = constants.ROOT_DIR
        existing["departments"]       = constants.DEPARTMENTS
        existing["artists"]           = constants.ARTISTS
        existing["ffmpeg_path"]       = constants.FFMPEG_PATH
        existing["blast_player_path"] = str(constants.BLAST_PLAYER_PATH)

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
