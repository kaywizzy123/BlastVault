import re as _re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

STUDIO_NAME = "NEON ANIMATION STUDIOS"
ROOT_DIR = r"C:\SHOWS"
ICONS_DIR = _ROOT / "icons"
ICON = str(ICONS_DIR / "bv.png")
CONFIG_PATH = _ROOT / "config.json"
THUMB_CACHE_DIR = _ROOT / "thumbnail_cache"
FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"

GRID_ICON_W    = 180          # icon width  — wider to fill 16:9 video frames
GRID_ICON_H    = 102          # icon height — ≈ 16:9 of width (180 × 9/16 ≈ 101)
GRID_ICON_SIZE = GRID_ICON_W  # kept for thumbnail-loader / icon-builder compat
GRID_CELL_SIZE = (196, 130)   # cell: slightly wider than icon + row for label
LIST_ICON_SIZE = 60

BORDER = "#0a0a0a"
BG = "#1A1A1A"
ACCENT_HI = "#1085d3"
ACCENT = "#0a5b91"
TEXT_PRI = "#ededed"
TEXT_SEC = "#a1a1a1"
FAIL = "#ad0303"
SUCCESS = "#03ad14"
SPLITTER_COLOR = "#292929"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"}
DOC_EXTS   = {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx"}
AUDIO_EXTS = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".aiff", ".m4a"}
OBJ_3D_EXTS = {".fbx", ".usd", ".usda", ".usdc", ".usdz"}

ALLOWED_EXTS = IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS | OBJ_3D_EXTS | DOC_EXTS

EXCLUDED_PATTERNS = []

DEPARTMENTS = [
    "All",
    "Story",
    "Visual Development",
    "Modeling",
    "Rigging",
    "Layout",
    "Layout Finaling",
    "Animation",
    "Character FX",
    "FX / Simulation",
    "Lighting",
    "Matte Painting",
]

# Maps lowercase filename tokens → department label.
# Tokens are produced by splitting the stem on  _  -  .  and whitespace.
DEPARTMENT_KEYWORDS: dict[str, str] = {
    "story":      "Story",
    "board":      "Story",
    "storyboard": "Story",
    "concept":    "Visual Development",
    "cncpt":      "Visual Development",
    "visdev":     "Visual Development",
    "model":      "Modeling",
    "mdl":        "Modeling",
    "geo":        "Modeling",
    "rig":        "Rigging",
    "rigging":    "Rigging",
    "layout":     "Layout",
    "rlo":        "Layout",
    "flo":        "Layout Finaling",
    "lyt":        "Layout",
    "anim":       "Animation",
    "anm":        "Animation",
    "animation":  "Animation",
    "cfx":        "Character FX",
    "charfx":     "Character FX",
    "charfin":    "Character FX",
    "fx":         "FX / Simulation",
    "sim":        "FX / Simulation",
    "vfx":        "FX / Simulation",
    "light":      "Lighting",
    "lgt":        "Lighting",
    "lighting":   "Lighting",
    "matte":      "Matte Painting",
    "mattepaint": "Matte Painting",
}

_SPLIT_RE   = _re.compile(r'[_\-.\s]+')
_VERSION_RE = _re.compile(r'_v(\d+)$', _re.IGNORECASE)


def version_key(stem: str) -> tuple:
    """Return ``(base_stem, version_int)`` if *stem* ends in ``_v###``, else ``(None, None)``."""
    m = _VERSION_RE.search(stem)
    if m:
        return stem[:m.start()], int(m.group(1))
    return None, None


def detect_department(filename: str) -> str:
    """Return the department for *filename* by matching tokens against DEPARTMENT_KEYWORDS.

    Example: ``char_anim_v001.mp4`` → ``"Animation"``
    Returns an empty string when no keyword matches.
    """
    stem = Path(filename).stem.lower()
    # Strip trailing version tag (_v001, _v1, …) before tokenising
    stem = _re.sub(r'_v\d+$', '', stem, flags=_re.IGNORECASE)
    tokens = set(_SPLIT_RE.split(stem))
    for kw, dept in DEPARTMENT_KEYWORDS.items():
        if kw in tokens:
            return dept
    return ""


def canonical_stem(base: str) -> str:
    """Remove department keyword tokens from a version-stripped stem.

    Used to group files that share an asset name but differ only by department tag,
    so only the highest-versioned file (across all departments) is shown per asset.

    Examples:
        ``char_hero_anim``  →  ``char_hero``
        ``seq_010_lgt``     →  ``seq_010``
        ``hero_cfx_v002``   →  ``hero``   (version should be stripped first)
    """
    tokens = _SPLIT_RE.split(base.lower())
    dept_keys = set(DEPARTMENT_KEYWORDS.keys())
    cleaned = [t for t in tokens if t not in dept_keys]
    result = "_".join(cleaned)
    # Fallback: if every token was a dept keyword, keep the original
    return result if result else base.lower()
