import os
import json
import fnmatch
from . import constants


def load_config():
    if os.path.exists(constants.CONFIG_PATH):
        try:
            with open(constants.CONFIG_PATH, "r") as f:
                data = json.load(f)
                constants.EXCLUDED_PATTERNS = data.get("excluded_patterns", [])
                constants.STUDIO_NAME = data.get("studio_name", constants.STUDIO_NAME)
                constants.ROOT_DIR = data.get("root_dir", constants.ROOT_DIR)
                constants.DEPARTMENTS = data.get("departments", constants.DEPARTMENTS)
                return data.get("catalogs", [])
        except Exception:
            constants.EXCLUDED_PATTERNS = []
    return []


def save_config(catalog_paths=None):
    try:
        existing = {}
        if os.path.exists(constants.CONFIG_PATH):
            with open(constants.CONFIG_PATH, "r") as f:
                existing = json.load(f)
        existing["excluded_patterns"] = constants.EXCLUDED_PATTERNS
        existing["studio_name"] = constants.STUDIO_NAME
        existing["root_dir"] = constants.ROOT_DIR
        existing["departments"] = constants.DEPARTMENTS
        if catalog_paths is not None:
            existing["catalogs"] = catalog_paths
        with open(constants.CONFIG_PATH, "w") as f:
            json.dump(existing, f, indent=2)
    except Exception:
        pass


def is_excluded(name):
    for pattern in constants.EXCLUDED_PATTERNS:
        if fnmatch.fnmatch(name.lower(), pattern.lower()):
            return True
    return False
