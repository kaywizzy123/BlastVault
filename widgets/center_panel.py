import sys
import os
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QAbstractItemView
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon

from core import constants
from core.config import is_excluded
from utils.icons import (
    colored_icon, make_placeholder_icon, get_file_icon,
    get_cached_video_icon, get_clapperboard_icon
)
from widgets.thumbnail_loader import ThumbnailLoader

_VERSION_RE = re.compile(r'_v(\d+)$', re.IGNORECASE)


def _version_key(stem):
    """Returns (base_stem, version_int) if stem ends in _v###, else (None, None)."""
    m = _VERSION_RE.search(stem)
    if m:
        return stem[:m.start()], int(m.group(1))
    return None, None


class CenterPanel(QWidget):
    folder_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.current_path = None
        self.is_grid_view = True
        self.thumbnail_loader = None
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(constants.GRID_ICON_SIZE, constants.GRID_ICON_SIZE))
        self.list_widget.setGridSize(QSize(*constants.GRID_CELL_SIZE))
        self.list_widget.setWordWrap(True)
        self.list_widget.setSpacing(2)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def create_layout(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.list_widget)

    def create_connections(self):
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

    def load_folder(self, path):
        self.current_path = path
        self.list_widget.clear()

        if self.thumbnail_loader and self.thumbnail_loader.isRunning():
            self.thumbnail_loader.stop()
            self.thumbnail_loader.terminate()
            self.thumbnail_loader.wait()

        icon_size = constants.GRID_ICON_SIZE if self.is_grid_view else constants.LIST_ICON_SIZE
        folder = Path(path)

        if folder.name.upper().startswith(("SEQ_", "SQ_", "SEQUENCE_")):
            self._load_latest_versions(folder, icon_size)
        else:
            self._load_direct(folder, icon_size)

    def _load_latest_versions(self, folder, icon_size):
        """Recursively show only the highest-version file per (base_stem, ext) group."""
        latest = {}      # (base_stem, ext) -> (version, Path)
        unversioned = [] # [Path]

        try:
            for root, dirs, files in os.walk(folder):
                dirs[:] = sorted(
                    [d for d in dirs if not is_excluded(d)],
                    key=str.lower
                )
                for fname in files:
                    p = Path(root) / fname
                    ext = p.suffix.lower()
                    if ext not in constants.ALLOWED_EXTS:
                        continue
                    base, version = _version_key(p.stem)
                    if base is not None:
                        key = (base, ext)
                        if key not in latest or version > latest[key][0]:
                            latest[key] = (version, p)
                    else:
                        unversioned.append(p)
        except PermissionError:
            pass

        display_paths = [p for _, p in latest.values()] + unversioned
        display_paths.sort(key=lambda p: p.name.lower())

        thumbnail_paths = []
        for p in display_paths:
            ext = p.suffix.lower()
            base, _ = _version_key(p.stem)
            item = QListWidgetItem(base if base is not None else p.stem)
            item.setData(Qt.UserRole, str(p))
            item.setData(Qt.UserRole + 1, False)
            if ext in constants.IMAGE_EXTS:
                item.setIcon(make_placeholder_icon(constants.BORDER, icon_size, "..."))
                thumbnail_paths.append(str(p))
            elif ext in constants.VIDEO_EXTS:
                cached = get_cached_video_icon(str(p), icon_size)
                if cached:
                    item.setIcon(cached)
                else:
                    item.setIcon(get_clapperboard_icon(icon_size))
                    thumbnail_paths.append(str(p))
            else:
                item.setIcon(get_file_icon(str(p), icon_size))
            self.list_widget.addItem(item)

        if thumbnail_paths:
            self.thumbnail_loader = ThumbnailLoader(thumbnail_paths, icon_size)
            self.thumbnail_loader.thumbnail_ready.connect(self.on_thumbnail_ready)
            self.thumbnail_loader.start()

    def _load_direct(self, folder, icon_size):
        """Show immediate contents: subfolders then files."""
        thumbnail_paths = []
        try:
            entries = sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            for p in entries:
                if p.is_dir() and is_excluded(p.name):
                    continue
                ext = p.suffix.lower()
                if p.is_file() and ext not in constants.ALLOWED_EXTS:
                    continue

                item = QListWidgetItem(p.name if p.is_dir() else p.stem)
                item.setData(Qt.UserRole, str(p))
                item.setData(Qt.UserRole + 1, p.is_dir())

                if p.is_dir():
                    item.setIcon(colored_icon(constants.ACCENT, closed=True, size=icon_size))
                elif ext in constants.IMAGE_EXTS:
                    item.setIcon(make_placeholder_icon(constants.BORDER, icon_size, "..."))
                    thumbnail_paths.append(str(p))
                elif ext in constants.VIDEO_EXTS:
                    cached = get_cached_video_icon(str(p), icon_size)
                    if cached:
                        item.setIcon(cached)
                    else:
                        item.setIcon(get_clapperboard_icon(icon_size))
                        thumbnail_paths.append(str(p))
                else:
                    item.setIcon(get_file_icon(str(p), icon_size))
                self.list_widget.addItem(item)
        except PermissionError:
            pass

        if thumbnail_paths:
            self.thumbnail_loader = ThumbnailLoader(thumbnail_paths, icon_size)
            self.thumbnail_loader.thumbnail_ready.connect(self.on_thumbnail_ready)
            self.thumbnail_loader.start()

    def on_thumbnail_ready(self, path, icon):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == path:
                item.setIcon(icon)
                break

    def on_item_double_clicked(self, item):
        if item.data(Qt.UserRole + 1):
            path = item.data(Qt.UserRole)
            self.load_folder(path)
            self.folder_changed.emit(path)

    def filter_items(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def toggle_view(self):
        self.is_grid_view = not self.is_grid_view
        if self.is_grid_view:
            self.list_widget.setViewMode(QListWidget.IconMode)
            self.list_widget.setIconSize(QSize(constants.GRID_ICON_SIZE, constants.GRID_ICON_SIZE))
            self.list_widget.setGridSize(QSize(*constants.GRID_CELL_SIZE))
            self.list_widget.setWordWrap(True)
        else:
            self.list_widget.setViewMode(QListWidget.ListMode)
            self.list_widget.setIconSize(QSize(constants.LIST_ICON_SIZE, constants.LIST_ICON_SIZE))
            self.list_widget.setGridSize(QSize())
        if self.current_path:
            self.load_folder(self.current_path)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from core.styles import styleSheet
    app = QApplication(sys.argv + ["-platform", "windows:darkmode=1"])
    app.setStyle("Fusion")
    app.setStyleSheet(styleSheet)
    w = CenterPanel()
    w.resize(900, 600)
    w.show()
    sys.exit(app.exec_())
