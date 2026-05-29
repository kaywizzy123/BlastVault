import sys
import os
import subprocess
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QAbstractItemView, QLabel, QApplication, QMenu, QStackedWidget,
)
from PyQt5.QtCore import Qt, QSize, QTimer, QEvent, QPoint, pyqtSignal, QFileSystemWatcher, QMimeData, QUrl
from PyQt5.QtGui import QIcon, QPixmap, QCursor, QDrag

from core import constants
from core.constants import detect_department, detect_artist, canonical_stem, version_key
from core.config import is_excluded
from core.meta import read_meta, read_folder_meta
from core.styles import context_menu_style
from utils.icons import (
    colored_icon, make_placeholder_icon, get_file_icon,
    get_cached_video_icon, get_clapperboard_icon, get_video_cache_path,
)
from widgets.thumbnail_loader import ThumbnailLoader

# Maximum side length (px) of the hover-preview popup image.
_PREVIEW_SIZE = 400


# ──────────────────────────────────────────────────────────────────────────── #
#  Drag-enabled list widget                                                     #
# ──────────────────────────────────────────────────────────────────────────── #

class FileListWidget(QListWidget):
    """QListWidget that emits proper file-URL MIME data when dragged, so
    external apps (Maya, Nuke, Photoshop, Finder, Explorer …) can receive
    the files directly."""

    def startDrag(self, _supported_actions):
        items = self.selectedItems()
        # Only drag files — skip folders
        file_items = [it for it in items if not it.data(Qt.UserRole + 1)]
        if not file_items:
            return

        urls = [QUrl.fromLocalFile(it.data(Qt.UserRole)) for it in file_items]
        mime = QMimeData()
        mime.setUrls(urls)

        drag = QDrag(self)
        drag.setMimeData(mime)

        # Use the item thumbnail as the drag pixmap for single-file drags
        if len(file_items) == 1:
            pix = file_items[0].icon().pixmap(64, 64)
            if not pix.isNull():
                drag.setPixmap(pix)
                drag.setHotSpot(pix.rect().center())

        drag.exec_(Qt.CopyAction)


# ──────────────────────────────────────────────────────────────────────────── #
#  Hover-preview popup                                                          #
# ──────────────────────────────────────────────────────────────────────────── #

class ThumbnailPreviewPopup(QWidget):
    """Frameless tooltip-style popup that shows a large thumbnail on hover."""

    def __init__(self):
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setStyleSheet(
            "background: #111111;"
            "border: 1px solid #444444;"
            "border-radius: 6px;"
        )
        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet("border: none;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self._label)

    def show_at(self, pixmap: QPixmap, cursor_pos: QPoint):
        if pixmap.isNull():
            return
        scaled = pixmap.scaled(
            _PREVIEW_SIZE, _PREVIEW_SIZE,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self._label.setPixmap(scaled)
        self.adjustSize()

        # Offset from cursor; flip to the opposite side if near a screen edge.
        screen = QApplication.desktop().screenGeometry(cursor_pos)
        x = cursor_pos.x() + 16
        y = cursor_pos.y() + 16
        if x + self.width()  > screen.right():
            x = cursor_pos.x() - self.width()  - 8
        if y + self.height() > screen.bottom():
            y = cursor_pos.y() - self.height() - 8
        self.move(x, y)
        self.show()
        self.raise_()

    def hide_preview(self):
        self.hide()


# ──────────────────────────────────────────────────────────────────────────── #
#  CenterPanel                                                                  #
# ──────────────────────────────────────────────────────────────────────────── #

class CenterPanel(QWidget):
    folder_changed   = pyqtSignal(str)
    items_loaded     = pyqtSignal(int)
    selection_changed = pyqtSignal(int)
    file_selected    = pyqtSignal(str)   # single file path, or "" if none/multi
    artists_found    = pyqtSignal(list)  # unique artist names in the loaded folder

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.current_path     = None
        self.is_grid_view     = True
        self.thumbnail_loader = None
        self._text_filter     = ""
        self._dept_filter     = "All"
        self._sort_mode       = "version_desc"   # "name" | "version_desc" | "version_asc"
        self._artist_filter   = "All"
        # (canonical, ext) -> {dept: Path, '_overall': Path}
        self._asset_versions: dict = {}
        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self._setup_watcher()

    # ------------------------------------------------------------------ #
    #  Widget / layout construction                                        #
    # ------------------------------------------------------------------ #

    def create_widgets(self):
        self.list_widget = FileListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(constants.GRID_ICON_W, constants.GRID_ICON_H))
        self.list_widget.setGridSize(QSize(*constants.GRID_CELL_SIZE))
        self.list_widget.setWordWrap(True)
        self.list_widget.setSpacing(2)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.setDragEnabled(True)
        self.list_widget.setDragDropMode(QAbstractItemView.DragOnly)

        # ── Loading indicator ────────────────────────────────────────────
        self._loading_label = QLabel("Loading")
        self._loading_label.setAlignment(Qt.AlignCenter)
        self._loading_label.setStyleSheet(f"""
            color: {constants.TEXT_SEC};
            font-size: 14px;
            background: transparent;
        """)
        self._dot_count = 0
        self._loading_timer = QTimer(self)
        self._loading_timer.setInterval(400)
        self._loading_timer.timeout.connect(self._animate_loading)

        # Hover-preview timers and popup
        self._preview_popup   = ThumbnailPreviewPopup()
        self._hovered_item    = None

        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(1500)          # 1.5 s before popup appears
        self._hover_timer.timeout.connect(self._show_hover_preview)

        self._autohide_timer = QTimer(self)
        self._autohide_timer.setSingleShot(True)
        self._autohide_timer.setInterval(10000)      # hide after 10 s of no movement
        self._autohide_timer.timeout.connect(self._preview_popup.hide_preview)

        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.installEventFilter(self)   # keyboard nav

        self.list_widget.setMouseTracking(True)
        self.list_widget.viewport().setMouseTracking(True)
        self.list_widget.viewport().installEventFilter(self)

    def create_layout(self):
        # Loading page — centred label shown while folder is being read
        loading_page = QWidget()
        lp_layout = QVBoxLayout(loading_page)
        lp_layout.addStretch()
        lp_layout.addWidget(self._loading_label)
        lp_layout.addStretch()

        self._stack = QStackedWidget()
        self._stack.addWidget(loading_page)      # index 0 — loading
        self._stack.addWidget(self.list_widget)  # index 1 — content
        self._stack.setCurrentIndex(1)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self._stack)

    def create_connections(self):
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)

    def _setup_watcher(self):
        """Initialise the folder watcher and its 2-second debounce timer."""
        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(self._on_directory_changed)

        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(2000)          # 2 s debounce
        self._reload_timer.timeout.connect(self._silent_reload)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def load_folder(self, path: str):
        self._show_loading()
        QApplication.processEvents()   # let Qt render the indicator before blocking

        self.current_path = path
        self._reset_hover()
        self.list_widget.clear()

        if self.thumbnail_loader and self.thumbnail_loader.isRunning():
            self.thumbnail_loader.stop()
            self.thumbnail_loader.terminate()
            self.thumbnail_loader.wait()

        # Keep the watcher pointed at the new folder
        for old in self._watcher.directories():
            self._watcher.removePath(old)
        self._watcher.addPath(path)

        icon_size = (
            (constants.GRID_ICON_W, constants.GRID_ICON_H)
            if self.is_grid_view
            else constants.LIST_ICON_SIZE
        )
        folder    = Path(path)

        if folder.name.upper().startswith(("SEQ_", "SQ_", "SEQUENCE_")):
            self._load_latest_versions(folder, icon_size)
        else:
            self._load_direct(folder, icon_size)

    def filter_items(self, text: str):
        """Filter by search text (connected to the search bar)."""
        self._text_filter = text
        self._apply_filters()

    def filter_department(self, dept: str):
        """Filter by department name; pass ``'All'`` to show everything."""
        self._dept_filter = dept
        self._apply_filters()

    def filter_artist(self, artist: str):
        """Filter by artist name; pass ``'All'`` to show everything."""
        self._artist_filter = artist
        self._apply_filters()

    def sort_items(self, label: str):
        """Change sort order and reload the current folder.

        *label* must match one of the header combobox option strings.
        """
        _MAP = {
            "Version (High → Low)":  "version_desc",
            "Version (Low → High)":  "version_asc",
        }
        self._sort_mode = _MAP.get(label, "name")
        if self.current_path:
            self.load_folder(self.current_path)

    def toggle_view(self):
        self.is_grid_view = not self.is_grid_view
        if self.is_grid_view:
            self.list_widget.setViewMode(QListWidget.IconMode)
            self.list_widget.setIconSize(QSize(constants.GRID_ICON_W, constants.GRID_ICON_H))
            self.list_widget.setGridSize(QSize(*constants.GRID_CELL_SIZE))
            self.list_widget.setWordWrap(True)
        else:
            self.list_widget.setViewMode(QListWidget.ListMode)
            self.list_widget.setIconSize(QSize(constants.LIST_ICON_SIZE, constants.LIST_ICON_SIZE))
            self.list_widget.setGridSize(QSize())
        if self.current_path:
            self.load_folder(self.current_path)

    # ------------------------------------------------------------------ #
    #  Folder loading                                                      #
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  Sort helpers                                                        #
    # ------------------------------------------------------------------ #

    def _entry_sort_key(self, p: Path) -> tuple:
        """Sort key for a single Path entry in _load_direct.

        Folders always come before files regardless of mode.  Within each
        group the order is determined by ``self._sort_mode``.
        """
        is_file = p.is_file()
        mode    = self._sort_mode

        # version_desc / version_asc
        _, ver = version_key(p.stem)
        if mode == "version_desc":
            v = -ver if ver is not None else float("inf")
        else:
            v = ver  if ver is not None else float("inf")
        return (is_file, v, p.name.lower())

    def _seq_sort_key(self, kv) -> object:
        """Sort key for items in _load_latest_versions.

        *kv* is ``((canonical, ext), (_, path))``.
        """
        _, (_, p) = kv
        mode = self._sort_mode

        # version_desc / version_asc
        _, ver = version_key(p.stem)
        if mode == "version_desc":
            return -ver if ver is not None else float("inf")
        else:
            return ver  if ver is not None else float("inf")

    def _load_latest_versions(self, folder: Path, icon_size: int):
        """Recursively build one item per (canonical_stem, ext) asset group.

        For each asset the most recently created file per department is tracked so
        the dept filter can swap to the right version rather than hiding the item.
        If the selected dept has no file for an asset the overall most-recent file
        is shown as a fallback — the item is never hidden by the dept filter.
        """
        # (canonical, dept, ext) -> (ctime, Path)  — best file per dept
        by_dept: dict[tuple, tuple] = {}
        # (canonical, ext)        -> (ctime, Path)  — best file overall (fallback)
        overall: dict[tuple, tuple] = {}

        try:
            for root, dirs, files in os.walk(folder):
                dirs[:] = sorted(
                    [d for d in dirs if not is_excluded(d)],
                    key=str.lower,
                )
                for fname in files:
                    p   = Path(root) / fname
                    ext = p.suffix.lower()
                    if ext not in constants.ALLOWED_EXTS:
                        continue
                    try:
                        ctime = constants.file_ctime(p)
                    except OSError:
                        continue

                    base, _    = version_key(p.stem)
                    stem_base  = base if base is not None else p.stem
                    can        = canonical_stem(stem_base, detect_artist(p.name))
                    dept       = detect_department(p.name)

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
            asset_versions.setdefault((can, ext), {})["_overall"] = p
        self._asset_versions = asset_versions

        # One item per asset, labelled by canonical stem
        thumbnail_paths = []
        artists: set[str] = set()
        for (can, ext), (_, p) in sorted(overall.items(), key=self._seq_sort_key):
            meta = read_meta(p)
            artist = meta.get("artist") or detect_artist(p.name)
            if artist:
                artists.add(artist)
            base, _ = version_key(p.stem)
            artist_token = (meta.get("artist") or detect_artist(p.name)).lower()
            label   = canonical_stem(base, artist_token) if base is not None else p.stem
            item    = self._make_file_item(label, p, ext, icon_size, thumbnail_paths, meta)
            item.setData(Qt.UserRole + 3, (can, ext))   # SEQ asset key
            self.list_widget.addItem(item)

        self._start_thumbnail_loader(thumbnail_paths, icon_size)
        self._hide_loading()
        self.items_loaded.emit(self.list_widget.count())
        self.artists_found.emit(sorted(artists))
        self._apply_filters()

    def _load_direct(self, folder: Path, icon_size: int):
        """Show immediate contents: subfolders first, then files."""
        # Read all .meta files in this folder in one pass
        folder_meta = read_folder_meta(folder)

        thumbnail_paths = []
        artists: set[str] = set()
        try:
            entries = sorted(folder.iterdir(), key=self._entry_sort_key)
            for p in entries:
                # Hide .meta subfolder and any user-excluded patterns
                if p.is_dir() and (p.name == ".meta" or is_excluded(p.name)):
                    continue
                ext = p.suffix.lower()
                if p.is_file() and ext not in constants.ALLOWED_EXTS:
                    continue

                if p.is_dir():
                    item = QListWidgetItem(p.name)
                    item.setData(Qt.UserRole,     str(p))
                    item.setData(Qt.UserRole + 1, True)
                    item.setData(Qt.UserRole + 2, "")
                    item.setData(Qt.UserRole + 4, "")
                    item.setIcon(colored_icon(constants.ACCENT, closed=True, size=icon_size))
                else:
                    meta = folder_meta.get(p.stem, {})
                    artist = meta.get("artist") or detect_artist(p.name)
                    if artist:
                        artists.add(artist)
                    item = self._make_file_item(p.stem, p, ext, icon_size, thumbnail_paths, meta)
                self.list_widget.addItem(item)
        except PermissionError:
            pass

        self._start_thumbnail_loader(thumbnail_paths, icon_size)
        self._hide_loading()
        self.items_loaded.emit(self.list_widget.count())
        self.artists_found.emit(sorted(artists))
        self._apply_filters()

    # ------------------------------------------------------------------ #
    #  Item / loader helpers                                               #
    # ------------------------------------------------------------------ #

    def _make_file_item(
        self, label: str, p: Path, ext: str,
        icon_size: int, thumbnail_paths: list,
        meta: dict | None = None,
    ) -> QListWidgetItem:
        """Build a QListWidgetItem for a file and queue thumbnails as needed."""
        meta = meta or {}
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole,     str(p))
        item.setData(Qt.UserRole + 1, False)
        # Department: meta wins over filename token detection
        item.setData(Qt.UserRole + 2, meta.get("department") or detect_department(p.name))
        # Artist: meta → filename convention fallback
        item.setData(Qt.UserRole + 4, meta.get("artist") or detect_artist(p.name))

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
        return item

    def _start_thumbnail_loader(self, paths: list, icon_size: int):
        if not paths:
            return
        self.thumbnail_loader = ThumbnailLoader(paths, icon_size)
        self.thumbnail_loader.thumbnail_ready.connect(self.on_thumbnail_ready)
        self.thumbnail_loader.start()

    def on_thumbnail_ready(self, path: str, icon: QIcon):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == path:
                item.setIcon(icon)
                break

    # ------------------------------------------------------------------ #
    #  Selection                                                           #
    # ------------------------------------------------------------------ #

    def _on_selection_changed(self):
        selected = self.list_widget.selectedItems()
        self.selection_changed.emit(len(selected))
        if len(selected) == 1 and not selected[0].data(Qt.UserRole + 1):
            self.file_selected.emit(selected[0].data(Qt.UserRole))
        else:
            self.file_selected.emit("")

    def on_item_double_clicked(self, item):
        path = item.data(Qt.UserRole)
        if item.data(Qt.UserRole + 1):   # is folder
            self.load_folder(path)
            self.folder_changed.emit(path)

    # ------------------------------------------------------------------ #
    #  Filtering                                                           #
    # ------------------------------------------------------------------ #

    def _apply_filters(self):
        """Apply text and department filters.

        SEQ items (``UserRole+3`` set): the dept filter swaps which file path is
        displayed — the item is never hidden. Falls back to the overall most-recent
        file when the chosen dept has no entry for an asset.

        All other items: the dept filter hides non-matching items as usual.
        """
        text   = self._text_filter.lower()
        dept   = self._dept_filter
        artist = self._artist_filter

        for i in range(self.list_widget.count()):
            item      = self.list_widget.item(i)
            is_folder = bool(item.data(Qt.UserRole + 1))
            name_ok   = (text in item.text().lower()) if text else True
            asset_key = item.data(Qt.UserRole + 3)   # None for non-SEQ items

            if is_folder:
                dept_ok = artist_ok = True
            elif asset_key is not None and asset_key in self._asset_versions:
                # SEQ item — swap path, never hide by dept/artist
                versions = self._asset_versions[asset_key]
                target   = versions.get(dept) if dept not in ("All", "") else None
                target   = target or versions.get("_overall")
                if target:
                    item.setData(Qt.UserRole,     str(target))
                    item.setData(Qt.UserRole + 2, detect_department(target.name))
                dept_ok = artist_ok = True
            else:
                dept_ok   = dept   in ("All", "") or item.data(Qt.UserRole + 2) == dept
                artist_ok = artist in ("All", "") or item.data(Qt.UserRole + 4) == artist

            item.setHidden(not (name_ok and dept_ok and artist_ok))

    # ------------------------------------------------------------------ #
    #  Hover-preview                                                       #
    # ------------------------------------------------------------------ #

    def eventFilter(self, obj, event):
        if obj is self.list_widget.viewport():
            etype = event.type()
            if etype == QEvent.MouseMove:
                item = self.list_widget.itemAt(event.pos())
                if item is not self._hovered_item:
                    self._reset_hover()
                    self._hovered_item = item
                    if item and not item.isHidden():
                        self._hover_timer.start()
            elif etype in (QEvent.Leave, QEvent.MouseButtonPress):
                self._reset_hover()
        elif obj is self.list_widget and event.type() == QEvent.KeyPress:
            key = event.key()
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self._on_enter_key()
                return True
            elif key == Qt.Key_Backspace:
                self._on_backspace_key()
                return True
            elif key == Qt.Key_F5:
                if self.current_path:
                    self.load_folder(self.current_path)
                return True
        return super().eventFilter(obj, event)

    def _show_hover_preview(self):
        item = self._hovered_item
        if item is None or item.isHidden():
            return
        path      = item.data(Qt.UserRole)
        is_folder = bool(item.data(Qt.UserRole + 1))
        if is_folder or not path:
            return

        ext    = Path(path).suffix.lower()
        pixmap = None
        if ext in constants.IMAGE_EXTS:
            pixmap = QPixmap(path)
        elif ext in constants.VIDEO_EXTS:
            cache = get_video_cache_path(path)
            if Path(cache).exists():
                pixmap = QPixmap(cache)

        if pixmap and not pixmap.isNull():
            self._preview_popup.show_at(pixmap, QCursor.pos())
            self._autohide_timer.start()

    # ------------------------------------------------------------------ #
    #  Thumbnail size                                                      #
    # ------------------------------------------------------------------ #

    def set_thumb_size(self, width: int):
        """Resize grid icons to *width* × (*width* × 9/16) and reload."""
        constants.GRID_ICON_W    = width
        constants.GRID_ICON_H    = width * 9 // 16
        constants.GRID_ICON_SIZE = width
        constants.GRID_CELL_SIZE = (width + 20, width * 9 // 16 + 28)
        self.list_widget.setIconSize(QSize(constants.GRID_ICON_W, constants.GRID_ICON_H))
        self.list_widget.setGridSize(QSize(*constants.GRID_CELL_SIZE))
        if self.current_path:
            self.load_folder(self.current_path)

    # ------------------------------------------------------------------ #
    #  Watch-folder auto-refresh                                           #
    # ------------------------------------------------------------------ #

    def _on_directory_changed(self, __path: str):
        """Received from QFileSystemWatcher; (re)starts the debounce timer."""
        self._reload_timer.start()    # calling start() on a running timer resets it

    def _silent_reload(self):
        """Reload the current folder while preserving the scroll position."""
        if not self.current_path:
            return
        sb  = self.list_widget.verticalScrollBar()
        pos = sb.value()
        self.load_folder(self.current_path)
        sb.setValue(pos)

    # ------------------------------------------------------------------ #
    #  Loading indicator                                                   #
    # ------------------------------------------------------------------ #

    def _show_loading(self):
        self._dot_count = 0
        self._loading_label.setText("Loading")
        self._stack.setCurrentIndex(0)
        self._loading_timer.start()

    def _hide_loading(self):
        self._loading_timer.stop()
        self._stack.setCurrentIndex(1)

    def _animate_loading(self):
        self._dot_count = (self._dot_count + 1) % 4
        self._loading_label.setText("Loading" + " ." * self._dot_count)

    # ------------------------------------------------------------------ #
    #  Keyboard navigation                                                 #
    # ------------------------------------------------------------------ #

    def _on_enter_key(self):
        """Enter / Return — navigate into the selected folder."""
        items = self.list_widget.selectedItems()
        if len(items) == 1 and items[0].data(Qt.UserRole + 1):
            path = items[0].data(Qt.UserRole)
            self.load_folder(path)
            self.folder_changed.emit(path)

    def _on_backspace_key(self):
        """Backspace — go up one folder level."""
        if not self.current_path:
            return
        parent = str(Path(self.current_path).parent)
        if parent != self.current_path:   # guard: already at filesystem root
            self.load_folder(parent)
            self.folder_changed.emit(parent)

    # ------------------------------------------------------------------ #
    #  Context menu                                                        #
    # ------------------------------------------------------------------ #

    def _show_context_menu(self, pos):
        items = self.list_widget.selectedItems()
        if not items:
            return

        menu = QMenu(self)
        menu.setStyleSheet(context_menu_style())
        paths = [it.data(Qt.UserRole) for it in items]

        if len(items) == 1:
            item      = items[0]
            path      = paths[0]
            is_folder = bool(item.data(Qt.UserRole + 1))

            if is_folder:
                open_act = menu.addAction("Open Folder")
                open_act.triggered.connect(lambda: (
                    self.load_folder(path), self.folder_changed.emit(path)
                ))
                menu.addSeparator()

            copy_path_act = menu.addAction("Copy Path")
            copy_path_act.triggered.connect(lambda: self._copy_to_clipboard(path))

            copy_name_act = menu.addAction("Copy Name")
            copy_name_act.triggered.connect(
                lambda: self._copy_to_clipboard(Path(path).name)
            )

            if not is_folder:
                menu.addSeparator()
                if sys.platform == "win32":
                    reveal_label = "Show in Explorer"
                elif sys.platform == "darwin":
                    reveal_label = "Reveal in Finder"
                else:
                    reveal_label = "Show in Files"
                reveal_act = menu.addAction(reveal_label)
                reveal_act.triggered.connect(lambda: self._reveal_in_explorer(path))
        else:
            copy_all_act = menu.addAction(f"Copy {len(items)} Paths")
            copy_all_act.triggered.connect(
                lambda: self._copy_to_clipboard("\n".join(paths))
            )

        menu.exec_(self.list_widget.viewport().mapToGlobal(pos))

    def _copy_to_clipboard(self, text: str):
        QApplication.clipboard().setText(text)

    def _reveal_in_explorer(self, path: str):
        """Open the file's parent folder and select/highlight the file."""
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", path])
            else:
                subprocess.Popen(["xdg-open", str(Path(path).parent)])
        except Exception as e:
            print(f"Could not reveal in explorer: {e}")

    # ------------------------------------------------------------------ #
    #  Hover-reset                                                         #
    # ------------------------------------------------------------------ #

    def _reset_hover(self):
        """Stop both timers and hide the popup."""
        self._hover_timer.stop()
        self._autohide_timer.stop()
        self._preview_popup.hide_preview()
        self._hovered_item = None


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from PyQt5.QtWidgets import QApplication
    from core.styles import styleSheet, qt_argv
    app = QApplication(qt_argv())
    app.setStyle("Fusion")
    app.setStyleSheet(styleSheet)
    w = CenterPanel()
    w.resize(900, 600)
    w.show()
    sys.exit(app.exec_())
