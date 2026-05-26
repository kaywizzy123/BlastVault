from pathlib import Path
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor

from core.constants import (
    BORDER, TEXT_PRI, THUMB_CACHE_DIR, ICONS_DIR,
    IMAGE_EXTS, AUDIO_EXTS, OBJ_3D_EXTS, DOC_EXTS
)


def colored_icon(color, closed=True, size=16):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    c = QColor(color)
    painter.setBrush(c)
    painter.setPen(Qt.NoPen)
    if closed:
        painter.drawRoundedRect(0, int(size * 0.25), int(size * 0.5), int(size * 0.19), 1, 1)
        painter.drawRoundedRect(0, int(size * 0.375), size, int(size * 0.5625), 1, 1)
    else:
        painter.drawRoundedRect(0, int(size * 0.1875), int(size * 0.5), int(size * 0.1875), 1, 1)
        painter.drawRoundedRect(0, int(size * 0.3125), size, int(size * 0.625), 1, 1)
        darker = QColor(color)
        darker.setAlpha(160)
        painter.setBrush(darker)
        painter.drawRoundedRect(int(size * 0.0625), int(size * 0.3125), int(size * 0.875), int(size * 0.1875), 1, 1)
    painter.end()
    return QIcon(pixmap)


def make_placeholder_icon(color, size, symbol="?"):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, size, size, 4, 4)
    painter.setPen(QColor(TEXT_PRI))
    font = painter.font()
    font.setPixelSize(max(size // 2, 8))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(QRect(0, 0, size, size), Qt.AlignCenter, symbol)
    painter.end()
    return QIcon(pixmap)


def get_file_icon(path, icon_size):
    ext = Path(path).suffix.lower()
    if ext in IMAGE_EXTS:
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            return QIcon(pixmap.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        return make_placeholder_icon(BORDER, icon_size, "IMG")
    elif ext in AUDIO_EXTS:
        return make_placeholder_icon("#2e1a2e", icon_size, "♫")
    elif ext in OBJ_3D_EXTS:
        return make_placeholder_icon("#2e2a1a", icon_size, "◆")
    elif ext in DOC_EXTS:
        return make_placeholder_icon("#1a2e1a", icon_size, "❐")
    else:
        return make_placeholder_icon(BORDER, icon_size, "•")


def get_video_cache_path(path):
    safe_name = path.replace("\\", "_").replace("/", "_").replace(":", "_")
    return str(THUMB_CACHE_DIR / (safe_name + "_thumb.jpg"))


def get_cached_video_icon(path, icon_size):
    cache_path = get_video_cache_path(path)
    if Path(cache_path).exists():
        pixmap = QPixmap(cache_path)
        if not pixmap.isNull():
            return QIcon(pixmap.scaled(
                icon_size, icon_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
    return None


def get_clapperboard_icon(icon_size):
    pixmap = QPixmap(str(ICONS_DIR / "clapperboard.png"))
    if not pixmap.isNull():
        return QIcon(pixmap.scaled(
            icon_size, icon_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        ))
    return make_placeholder_icon("#1a1a2e", icon_size, "▶")
