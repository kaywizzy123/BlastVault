import subprocess
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap

from core import constants
from utils.icons import (
    get_file_icon, get_video_cache_path, _letterbox_icon, get_clapperboard_icon,
)


class ThumbnailLoader(QThread):
    thumbnail_ready = pyqtSignal(str, QIcon)

    def __init__(self, tasks, icon_size):
        super().__init__()
        self.tasks = tasks
        self.icon_size = icon_size
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        for path in self.tasks:
            if not self._running:
                break
            ext = Path(path).suffix.lower()
            if ext in constants.VIDEO_EXTS:
                icon = self._load_video_thumbnail(path)
            else:
                icon = get_file_icon(path, self.icon_size)
            if icon:
                self.thumbnail_ready.emit(path, icon)

    def _load_video_thumbnail(self, path: str) -> QIcon:
        ffmpeg = Path(constants.FFMPEG_PATH)   # read live — respects Settings changes
        if not ffmpeg.exists():
            return get_clapperboard_icon(self.icon_size)

        try:
            constants.THUMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path = get_video_cache_path(path)

            if not Path(cache_path).exists():
                result = subprocess.run(
                    [
                        str(ffmpeg), "-y",
                        "-i", path,
                        "-vframes", "1",
                        "-q:v", "2",
                        cache_path,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=15,
                )
                if result.returncode != 0:
                    return get_clapperboard_icon(self.icon_size)

            if Path(cache_path).exists():
                pixmap = QPixmap(cache_path)
                if not pixmap.isNull():
                    return _letterbox_icon(pixmap, self.icon_size)
        except Exception as e:
            print(f"Video thumbnail error for {path}: {e}")

        return get_clapperboard_icon(self.icon_size)
