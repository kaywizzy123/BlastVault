import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STUDIO_NAME = "NEON ANIMATION STUDIOS"
ROOT_DIR = r"C:\SHOWS"
ICONS_DIR = os.path.join(_ROOT, "icons")
ICON = os.path.join(ICONS_DIR, "bv.png")
CONFIG_PATH = os.path.join(_ROOT, "config.json")
THUMB_CACHE_DIR = os.path.join(_ROOT, "thumbnail_cache")
FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"

GRID_ICON_SIZE = 160
GRID_CELL_SIZE = (180, 200)
LIST_ICON_SIZE = 48

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
    "Concept Art",
    "Modeling",
    "Rigging",
    "Layout",
    "Animation",
    "Character FX",
    "FX / Simulation",
    "Lighting",
    "Matte Painting",
]
