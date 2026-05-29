import hashlib
import os
from pathlib import Path
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor

from core.constants import (
    BORDER, TEXT_PRI, THUMB_CACHE_DIR, ICONS_DIR,
    IMAGE_EXTS, AUDIO_EXTS, OBJ_3D_EXTS, DOC_EXTS,
)

# Subdirectory of THUMB_CACHE_DIR used for scaled image thumbnails.
# Created lazily on first use so startup cost stays zero.
_IMG_CACHE_DIR: Path | None = None


def _img_cache_dir() -> Path:
    global _IMG_CACHE_DIR
    if _IMG_CACHE_DIR is None:
        _IMG_CACHE_DIR = THUMB_CACHE_DIR / "img"
        _IMG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _IMG_CACHE_DIR


def _img_cache_path(path: str, w: int, h: int) -> Path:
    """Return the cache-file path for a scaled image thumbnail.

    The key encodes the source path, its mtime, and the target size so that:

    * modifying the source file → different mtime → cache miss (old entry orphaned)
    * changing the thumbnail-size slider → different WxH → fresh entry at new size
    """
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = 0.0
    digest = hashlib.md5(f"{path}:{mtime}:{w}x{h}".encode()).hexdigest()
    return _img_cache_dir() / f"{digest}.jpg"


# ──────────────────────────────────────────────────────────────────────────── #
#  Internal helpers                                                             #
# ──────────────────────────────────────────────────────────────────────────── #

def _wh(size) -> tuple[int, int]:
    """Return ``(width, height)`` from either an ``int`` or a ``(w, h)`` tuple."""
    return (size, size) if isinstance(size, int) else tuple(size)


# ──────────────────────────────────────────────────────────────────────────── #
#  Icon builders                                                                #
# ──────────────────────────────────────────────────────────────────────────── #

def _letterbox_icon(pixmap: QPixmap, size) -> QIcon:
    """Scale *pixmap* preserving aspect ratio, then pad with black to fill the
    target canvas.  *size* may be an ``int`` (square) or a ``(w, h)`` tuple."""
    w, h = _wh(size)
    scaled = pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    canvas = QPixmap(w, h)
    canvas.fill(Qt.black)
    painter = QPainter(canvas)
    painter.drawPixmap((w - scaled.width()) // 2, (h - scaled.height()) // 2, scaled)
    painter.end()
    return QIcon(canvas)


def _fill_icon(pixmap: QPixmap, size) -> QIcon:
    """Centre-crop *pixmap* to fill the target canvas exactly.
    *size* may be an ``int`` (square) or a ``(w, h)`` tuple."""
    w, h = _wh(size)
    scaled = pixmap.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = (scaled.width()  - w) // 2
    y = (scaled.height() - h) // 2
    return QIcon(scaled.copy(x, y, w, h))


def colored_icon(color, closed=True, size=16):
    """Folder icon sized to fill the full *size* area.
    *size* may be an ``int`` (square) or a ``(w, h)`` tuple.

    The tab is drawn first, then the body is painted on top — its top edge
    covers the tab's rounded bottom corners so the two shapes read as one.
    """
    w, h   = _wh(size)
    r      = max(min(w, h) // 10, 2)
    body_y = int(h * 0.18)
    tab_w  = int(w * 0.45)
    tab_h  = body_y + r * 4    # overlap ensures seamless join

    pixmap = QPixmap(w, h)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.NoPen)

    # 1. Tab — drawn first so the body can cover its bottom rounded edge
    painter.drawRoundedRect(0, 0, tab_w, tab_h, r, r)

    # 2. Body — starts at body_y and covers the tab's bottom, unifying the shape
    painter.drawRoundedRect(0, body_y, w, h - body_y, r, r)

    if not closed:
        # Darken the inner area to suggest the folder is open
        inner = QColor(color)
        inner.setAlpha(150)
        painter.setBrush(inner)
        m = max(r, int(min(w, h) * 0.08))
        painter.drawRoundedRect(m, body_y + m, w - 2 * m, h - body_y - 2 * m, max(r - 2, 2), max(r - 2, 2))

    painter.end()
    return QIcon(pixmap)


def make_placeholder_icon(color, size, symbol: str = "?") -> QIcon:
    """Rounded-rectangle placeholder icon.
    *size* may be an ``int`` (square) or a ``(w, h)`` tuple."""
    w, h = _wh(size)
    pixmap = QPixmap(w, h)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, w, h, 4, 4)
    painter.setPen(QColor(TEXT_PRI))
    font = painter.font()
    font.setPixelSize(max(min(w, h) // 2, 8))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(QRect(0, 0, w, h), Qt.AlignCenter, symbol)
    painter.end()
    return QIcon(pixmap)


# ──────────────────────────────────────────────────────────────────────────── #
#  File-type icon dispatcher                                                    #
# ──────────────────────────────────────────────────────────────────────────── #

def get_file_icon(path, icon_size) -> QIcon:
    ext = Path(path).suffix.lower()

    if ext in IMAGE_EXTS:
        w, h  = _wh(icon_size)
        cache = _img_cache_path(path, w, h)

        # ── Cache hit: tiny pre-scaled JPEG → near-zero decode cost ───────
        if cache.exists():
            pix = QPixmap(str(cache))
            if not pix.isNull():
                return QIcon(pix)

        # ── Cache miss: load original, crop to target size, persist ───────
        pix = QPixmap(path)
        if not pix.isNull():
            scaled  = pix.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x       = (scaled.width()  - w) // 2
            y       = (scaled.height() - h) // 2
            cropped = scaled.copy(x, y, w, h)
            try:
                cropped.save(str(cache), "JPEG", 85)
            except Exception:
                pass   # cache write failure is non-fatal
            return QIcon(cropped)

        return make_placeholder_icon(BORDER, icon_size, "IMG")

    elif ext in AUDIO_EXTS:
        return make_placeholder_icon("#2e1a2e", icon_size, "♫")
    elif ext in OBJ_3D_EXTS:
        return make_placeholder_icon("#2e2a1a", icon_size, "◆")
    elif ext in DOC_EXTS:
        return make_placeholder_icon("#1a2e1a", icon_size, "❐")
    else:
        return make_placeholder_icon(BORDER, icon_size, "•")


# ──────────────────────────────────────────────────────────────────────────── #
#  Video thumbnail helpers                                                      #
# ──────────────────────────────────────────────────────────────────────────── #

def get_video_cache_path(path: str) -> str:
    safe = path.replace("\\", "_").replace("/", "_").replace(":", "_")
    return str(THUMB_CACHE_DIR / (safe + "_thumb.jpg"))


def get_cached_video_icon(path, icon_size) -> QIcon | None:
    cache_path = get_video_cache_path(path)
    if Path(cache_path).exists():
        pixmap = QPixmap(cache_path)
        if not pixmap.isNull():
            return _letterbox_icon(pixmap, icon_size)
    return None


def get_clapperboard_icon(icon_size) -> QIcon:
    w, h   = _wh(icon_size)
    pixmap = QPixmap(str(ICONS_DIR / "clapperboard.png"))
    if not pixmap.isNull():
        return QIcon(pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    return make_placeholder_icon("#1a1a2e", icon_size, "▶")
