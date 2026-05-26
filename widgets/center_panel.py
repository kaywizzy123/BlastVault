import sys
import os
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QAbstractItemView
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon

from core import constants
from core.constants import detect_department, canonical_stem
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
    items_loaded = pyqtSignal(int)
    selection_changed = pyqtSignal(int)
    file_selected = pyqtSignal(str)   # emits path when exactly one file is selected, else ""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.current_path = None
        self.is_grid_view = True
        self.thumbnail_loader = None
        self._text_filter = ""
        self._dept_filter = "All"
        self._asset_versions: dict = {}   # (canonical, ext) -> {dept: Path, '_overall': Path}
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
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        selected = self.list_widget.selectedItems()
        self.selection_changed.emit(len(selected))
        if len(selected) == 1 and not selected[0].data(Qt.UserRole + 1):
            self.file_selected.emit(selected[0].data(Qt.UserRole))
        else:
            self.file_selected.emit("")

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
        """Recursively build one item per (canonical_stem, ext) asset group.

        For each asset, the most recently created file per department is stored so that
        the dept filter can swap to the right version rather than hiding the item.
        If the selected department has no file for an asset, the overall most recent
        file is shown as a fallback — the item is never hidden by the dept filter.
        """
        # (canonical, dept, ext) -> (ctime, Path) — best file per dept variant
        by_dept: dict[tuple, tuple] = {}
        # (canonical, ext)        -> (ctime, Path) — best file overall (fallback)
        overall: dict[tuple, tuple] = {}

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
                    try:
                        ctime = p.stat().st_ctime
                    except OSError:
                        continue
                    base, _ = _version_key(p.stem)
                    stem_for_key = base if base is not None else p.stem
                    can  = canonical_stem(stem_for_key)
                    dept = detect_department(p.name)

                    dept_key = (can, dept, ext)
                    if dept_key not in by_dept or ctime > by_dept[dept_key][0]:
                        by_dept[dept_key] = (ctime, p)

                    overall_key = (can, ext)
                    if overall_key not in overall or ctime > overall[overall_key][0]:
                        overall[overall_key] = (ctime, p)
        except PermissionError:
            pass

        # Build lookup: (canonical, ext) -> {dept: Path, '_overall': Path}
        asset_versions: dict[tuple, dict] = {}
        for (can, dept, ext), (_, p) in by_dept.items():
            asset_versions.setdefault((can, ext), {})[dept] = p
        for (can, ext), (_, p) in overall.items():
            asset_versions.setdefault((can, ext), {})['_overall'] = p
        self._asset_versions = asset_versions

        # One item per asset, initially showing the overall most-recent file
        display = sorted(overall.items(), key=lambda kv: kv[1][1].name.lower())
        thumbnail_paths = []
        for (can, ext), (_, p) in display:
            base, _ = _version_key(p.stem)
            label = canonical_stem(base) if base is not None else p.stem
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole,     str(p))
            item.setData(Qt.UserRole + 1, False)
            item.setData(Qt.UserRole + 2, detect_department(p.name))
            item.setData(Qt.UserRole + 3, (can, ext))   # key into _asset_versions
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

        self.items_loaded.emit(self.list_widget.count())
        self._apply_filters()

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
                item.setData(Qt.UserRole + 2, "" if p.is_dir() else detect_department(p.name))

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

        self.items_loaded.emit(self.list_widget.count())
        self._apply_filters()

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
        """Filter by search text (called by the search bar)."""
        self._text_filter = text
        self._apply_filters()

    def filter_department(self, dept):
        """Filter by department name, e.g. 'Animation'. Pass 'All' to show everything."""
        self._dept_filter = dept
        self._apply_filters()

    def _apply_filters(self):
        """Apply text and department filters.

        SEQ items (UserRole+3 is set): dept filter swaps which file version is
        displayed — the item is never hidden. If no file of the chosen department
        exists for an asset, the overall most-recent file is shown as a fallback.

        All other items: dept filter hides non-matching items as usual.
        """
        text = self._text_filter.lower()
        dept = self._dept_filter
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            is_folder = bool(item.data(Qt.UserRole + 1))
            name_match = (text in item.text().lower()) if text else True

            asset_key = item.data(Qt.UserRole + 3)   # set only for SEQ items
            if is_folder:
                dept_match = True
            elif asset_key is not None and asset_key in self._asset_versions:
                # SEQ item: swap to the right dept version, never hide
                versions = self._asset_versions[asset_key]
                if dept in ("All", ""):
                    target = versions.get('_overall')
                else:
                    target = versions.get(dept) or versions.get('_overall')
                if target:
                    item.setData(Qt.UserRole,     str(target))
                    item.setData(Qt.UserRole + 2, detect_department(target.name))
                dept_match = True
            else:
                # Regular (non-SEQ) item: hide if dept doesn't match
                dept_match = dept in ("All", "") or item.data(Qt.UserRole + 2) == dept
            item.setHidden(not (name_match and dept_match))

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
