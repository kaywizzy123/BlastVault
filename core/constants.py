import re as _re
import shutil as _shutil
import sys as _sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

STUDIO_NAME = "INDIE ANIMATION STUDIOS"
ICONS_DIR = _ROOT / "icons"
ICON = str(ICONS_DIR / "bv.png")

# ---------------------------------------------------------------------------
# User-data paths
#   Dev  (running from source)  →  project folder, easy to inspect/reset
#   Prod (packaged by PyInstaller) →  per-user OS directory, always writable
# ---------------------------------------------------------------------------
_IS_FROZEN = getattr(_sys, "frozen", False)

if _IS_FROZEN:
    # Installed / packaged — use the proper OS user-data location
    if _sys.platform == "win32":
        _APP_DATA  = Path.home() / "AppData" / "Roaming" / "BlastVault"
        _CACHE_DIR = _APP_DATA / "thumbnail_cache"
    elif _sys.platform == "darwin":
        _APP_DATA  = Path.home() / "Library" / "Application Support" / "BlastVault"
        _CACHE_DIR = Path.home() / "Library" / "Caches" / "BlastVault" / "thumbnail_cache"
    else:                               # Linux / other
        _APP_DATA  = Path.home() / ".config" / "BlastVault"
        _CACHE_DIR = Path.home() / ".cache"  / "BlastVault" / "thumbnail_cache"
else:
    # Development — keep everything inside the project folder
    _APP_DATA  = _ROOT
    _CACHE_DIR = _ROOT / "thumbnail_cache"

CONFIG_PATH     = _APP_DATA  / "config.json"
THUMB_CACHE_DIR = _CACHE_DIR

# Ensure both directories exist at import time so nothing else needs to mkdir.
_APP_DATA.mkdir(parents=True, exist_ok=True)
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Platform-specific defaults
if _sys.platform == "win32":
    ROOT_DIR = r"C:\SHOWS"
else:
    ROOT_DIR = str(Path.home() / "Shows")

# FFMPEG_PATH — auto-detected at startup; never saved to / restored from config.
# Resolution order:
#   1. PATH  (shutil.which)  — covers Homebrew, conda, apt, winget, etc.
#   2. Common hard-coded locations — safety net for out-of-PATH installs
if _sys.platform == "win32":
    _FFMPEG_FALLBACKS = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
elif _sys.platform == "darwin":
    _FFMPEG_FALLBACKS = [
        "/opt/homebrew/bin/ffmpeg",   # Apple Silicon Homebrew
        "/usr/local/bin/ffmpeg",      # Intel Homebrew / manual install
    ]
else:
    _FFMPEG_FALLBACKS = ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]

FFMPEG_PATH: str = (
    _shutil.which("ffmpeg")
    or next((c for c in _FFMPEG_FALLBACKS if Path(c).exists()), "")
)

# Path to the BlastPlayer entry-point.  Candidates are checked in order;
# the first existing file wins.  Falls back to the sibling-directory path
# even when nothing is found so callers always have a displayable string.
_BLAST_PLAYER_CANDIDATES = [
    _ROOT.parent / "BlastPlayer" / "main.py",   # sibling directory (default layout)
    _ROOT / "BlastPlayer" / "main.py",           # embedded sub-directory
    Path.home() / "BlastPlayer" / "main.py",     # home-directory install
]
BLAST_PLAYER_PATH: Path = next(
    (c for c in _BLAST_PLAYER_CANDIDATES if c.is_file()),
    _BLAST_PLAYER_CANDIDATES[0],  # default even when not found
)

# Window / splitter state — persisted across sessions via config.json.
WINDOW_MAXIMIZED: bool  = True
WINDOW_GEOMETRY:  tuple = ()    # (x, y, w, h) — empty → default (maximised)
SPLITTER_SIZES:   list  = []    # empty → use hardcoded defaults in MainWindow

# Supervisor PIN (SHA-256 hex digest).  Empty string = no PIN set yet.
SUPERVISOR_PIN_HASH: str = ""
# Runtime lock state — True = locked (default), False = supervisor unlocked.
STATUS_LOCKED: bool = True

GRID_ICON_W    = 180          # icon width  — 16:9 asset grid
GRID_ICON_H    = 102          # icon height — ≈ 16:9 of width (180 × 9/16 ≈ 101)
GRID_ICON_SIZE = GRID_ICON_W  # kept for thumbnail-loader / icon-builder compat
GRID_CELL_SIZE = (196, 130)   # cell: slightly wider than icon + row for label
LIST_ICON_SIZE = 60

BORDER = "#0a0a0a"
BG = "#1A1A1A"
ACCENT_HI = "#1085d3"
ACCENT = "#343434"
TEXT_PRI = "#ededed"
TEXT_SEC = "#a1a1a1"
FAIL = "#ad0303"
SUCCESS = "#03ad14"
SPLITTER_COLOR = "#292929"

# ── Asset status ─────────────────────────────────────────────────────────── #
STATUS_OPTIONS: list[str] = ["WIP", "Review", "Approved", "Revision", "On Hold"]

STATUS_COLORS: dict[str, str] = {
    "WIP":      "#e5a820",   # amber
    "Review":   "#1085d3",   # blue  (same as ACCENT_HI)
    "Approved": "#03ad14",   # green (same as SUCCESS)
    "Revision": "#a1a1a1",   # grey  (same as TEXT_SEC)
    "On Hold":  "#ad0303",   # red   (same as FAIL)
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"}
DOC_EXTS   = {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx"}
AUDIO_EXTS = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".aiff", ".m4a"}
OBJ_3D_EXTS = {".fbx", ".usd", ".usda", ".usdc", ".usdz"}

# Only video, image, and audio files are surfaced in the browser.
# DOC_EXTS / OBJ_3D_EXTS are kept as named sets so icons.py can still
# generate placeholder icons if it ever encounters those file types.
ALLOWED_EXTS = IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS

EXCLUDED_PATTERNS = []

ARTISTS: list[str] = ["All"]   # populated from config; "All" always first

DEPARTMENTS = [
    "All",
    "Story",
    "Layout",
    "Layout Finaling",
    "Animation",
    "Character FX",
    "FX / Simulation",
    "Lighting",
    "Compositing",
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
    "comp":        "Compositing",
    "composite":   "Compositing",
    "compositing": "Compositing",
    "matte":       "Matte Painting",
    "mattepaint":  "Matte Painting",
}

_SPLIT_RE   = _re.compile(r'[_\-.\s]+')
_VERSION_RE = _re.compile(r'_v(\d+)$', _re.IGNORECASE)


def version_key(stem: str) -> tuple:
    """Return ``(base_stem, version_int)`` if *stem* ends in ``_v###``, else ``(None, None)``."""
    m = _VERSION_RE.search(stem)
    if m:
        return stem[:m.start()], int(m.group(1))
    return None, None


def detect_artist(filename: str) -> str:
    """Return the artist name from *filename* using the studio naming convention:

        ``<name>_<dept>_<artist>_v<version>``

    The artist is the last token of the version-stripped stem, provided it
    is not itself a recognised department keyword.

    Example: ``goat_fit0700_anim_oogunremi_v001.ma`` → ``"oogunremi"``
    Returns an empty string when the pattern is not matched.
    """
    stem   = Path(filename).stem.lower()
    stem   = _re.sub(r'_v\d+$', '', stem, flags=_re.IGNORECASE)
    tokens = _SPLIT_RE.split(stem)
    if not tokens:
        return ""
    last = tokens[-1]
    # Guard: don't return a department keyword as an artist name
    if last in DEPARTMENT_KEYWORDS:
        return ""
    return last


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


def file_ctime(p: Path) -> float:
    """Return the best available creation/birth time for *p*.

    * Windows / macOS — ``st_birthtime`` (true creation time).
    * Linux           — ``st_mtime`` (modification time; Linux does not expose
                         a creation timestamp through the standard stat API).
    """
    st = p.stat()
    try:
        return st.st_birthtime      # Windows, macOS
    except AttributeError:
        return st.st_mtime          # Linux fallback


def canonical_stem(base: str, artist: str = "") -> str:
    """Remove department and artist tokens from a version-stripped stem.

    Used to group files that share an asset name but differ only by department
    or artist tag, so only the latest file is shown per asset in SEQ view.

    Examples (with convention ``<name>_<dept>_<artist>_v###``):
        ``char_hero_anim_oogunremi``  →  ``char_hero``
        ``seq_010_lgt``               →  ``seq_010``
        ``hero_cfx_v002``             →  ``hero``  (version stripped by caller)

    *artist* should be the lower-cased artist token so it can be removed.
    When omitted, only department keywords are stripped.
    """
    tokens    = _SPLIT_RE.split(base.lower())
    dept_keys = set(DEPARTMENT_KEYWORDS.keys())
    cleaned   = [t for t in tokens if t not in dept_keys]
    # Strip the artist token when it appears at the end of the cleaned list
    if artist and cleaned and cleaned[-1] == artist.lower():
        cleaned = cleaned[:-1]
    result = "_".join(cleaned)
    # Fallback: if every token was stripped, keep the original
    return result if result else base.lower()
