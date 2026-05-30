import sys
import os
import subprocess
import threading
import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QAbstractItemView, QLabel, QApplication, QMenu, QStackedWidget,
    QPushButton, QStyledItemDelegate, QScrollArea, QFrame,
)
from PyQt5.QtCore import Qt, QSize, QTimer, QEvent, QPoint, pyqtSignal, QFileSystemWatcher, QMimeData, QUrl
from PyQt5.QtGui import QIcon, QPixmap, QCursor, QDrag, QPainter, QPen, QColor

from core import constants
from core.constants import detect_department, detect_artist, canonical_stem, version_key
from core.config import is_excluded, has_media_or_subfolders
from core.meta import read_meta, read_folder_meta, write_meta
from core.notes import has_notes
from core.styles import context_menu_style
from utils.icons import (
    colored_icon, make_placeholder_icon, get_file_icon,
    get_cached_video_icon, get_clapperboard_icon, get_video_cache_path,
)
from widgets.thumbnail_loader import ThumbnailLoader

# Maximum side length (px) of the hover-preview popup image.
_PREVIEW_SIZE = 400


# ──────────────────────────────────────────────────────────────────────────── #
#  Status badge delegate                                                        #
# ──────────────────────────────────────────────────────────────────────────── #

class StatusBadgeDelegate(QStyledItemDelegate):
    """Draws overlay badges on each grid/list icon:
      • bottom-right — pipeline status colour dot  (UserRole + 5)
      • top-left     — note.png icon               (UserRole + 6)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Pre-load the notes icon once; scaled versions cached on first use.
        self._note_pix_src = QPixmap(str(constants.ICONS_DIR / "note.png"))
        self._note_pix_cache: dict[int, QPixmap] = {}  # size → scaled pixmap

    def _note_pix(self, size: int) -> QPixmap:
        """Return a *size×size* version of the notes icon (cached)."""
        if size not in self._note_pix_cache:
            self._note_pix_cache[size] = self._note_pix_src.scaled(
                size, size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        return self._note_pix_cache[size]

    def paint(self, painter, option, index):
        # Let Qt draw the normal item first (icon + label + selection highlight)
        super().paint(painter, option, index)

        status    = index.data(Qt.UserRole + 5)
        note_flag = bool(index.data(Qt.UserRole + 6))

        if not status and not note_flag:
            return

        dec_w = option.decorationSize.width()
        dec_h = option.decorationSize.height()

        # Qt centres the icon horizontally and adds a small top margin (~4 px).
        cell   = option.rect
        icon_x = cell.x() + (cell.width() - dec_w) // 2
        icon_y = cell.y() + 4

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # ── Status dot — bottom-right ────────────────────────────────────
        if status:
            color = constants.STATUS_COLORS.get(status)
            if color:
                r  = 10 if dec_w >= 80 else 7
                cx = icon_x + dec_w - r - 3
                cy = icon_y + dec_h - r - 3
                painter.setPen(QPen(QColor("#000000"), 2))
                painter.setBrush(QColor(color))
                painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # ── Notes icon — top-left ────────────────────────────────────────
        if note_flag and not self._note_pix_src.isNull():
            icon_size = 18 if dec_w >= 80 else 13
            pix = self._note_pix(icon_size)
            painter.drawPixmap(icon_x + 3, icon_y + 3, pix)

        painter.restore()


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
#  Version history popup                                                        #
# ──────────────────────────────────────────────────────────────────────────── #

class VersionCard(QWidget):
    """Single clickable card inside the version history popup."""
    version_clicked = pyqtSignal(str)   # absolute path

    THUMB_W = 90
    THUMB_H = 51    # 16:9
    CARD_W  = 100
    CARD_H  = 122

    def __init__(self, p: Path, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self._path = str(p)
        self.setFixedSize(self.CARD_W, self.CARD_H)
        self._normal_style = (
            f"QWidget {{ background:{constants.BG}; border-radius:5px;"
            f" border:1px solid {constants.SPLITTER_COLOR}; }}"
        )
        self._hover_style = (
            f"QWidget {{ background:{constants.ACCENT}; border-radius:5px;"
            f" border:1px solid {constants.ACCENT_HI}; }}"
        )
        self.setStyleSheet(self._normal_style)

        # ── Thumbnail ────────────────────────────────────────────────────
        thumb_lbl = QLabel()
        thumb_lbl.setFixedSize(self.THUMB_W, self.THUMB_H)
        thumb_lbl.setAlignment(Qt.AlignCenter)
        thumb_lbl.setStyleSheet("background:#000; border-radius:3px; border:none;")

        # Read meta once — used by both department and status sections below
        meta = read_meta(p)

        ext = p.suffix.lower()
        if ext in constants.IMAGE_EXTS:
            icon = get_file_icon(str(p), (self.THUMB_W, self.THUMB_H))
        elif ext in constants.VIDEO_EXTS:
            icon = (get_cached_video_icon(str(p), (self.THUMB_W, self.THUMB_H))
                    or get_clapperboard_icon((self.THUMB_W, self.THUMB_H)))
        else:
            icon = None
        if icon:
            thumb_lbl.setPixmap(icon.pixmap(self.THUMB_W, self.THUMB_H))

        # ── Version label ────────────────────────────────────────────────
        _, ver = version_key(p.stem)
        ver_lbl = QLabel(f"v{ver:03d}" if ver is not None else p.stem[-4:])
        ver_lbl.setAlignment(Qt.AlignCenter)
        ver_lbl.setStyleSheet(
            f"color:{constants.TEXT_PRI}; font-size:11px; font-weight:bold;"
            f" background:transparent; border:none;"
        )

        # ── Department ───────────────────────────────────────────────────
        dept = meta.get("department") or detect_department(p.name)
        dept_lbl = QLabel(dept if dept else "—")
        dept_lbl.setAlignment(Qt.AlignCenter)
        dept_lbl.setStyleSheet(
            f"color:{constants.TEXT_SEC}; font-size:9px;"
            f" background:transparent; border:none;"
        )

        # ── Date ─────────────────────────────────────────────────────────
        try:
            ctime    = constants.file_ctime(p)
            date_str = datetime.datetime.fromtimestamp(ctime).strftime("%Y-%m-%d")
        except Exception:
            date_str = ""
        date_lbl = QLabel(date_str)
        date_lbl.setAlignment(Qt.AlignCenter)
        date_lbl.setStyleSheet(
            f"color:{constants.TEXT_SEC}; font-size:9px;"
            f" background:transparent; border:none;"
        )

        # ── Status dot + label ───────────────────────────────────────────
        status     = meta.get("status", "")
        dot_color  = constants.STATUS_COLORS.get(status, constants.SPLITTER_COLOR)
        dot        = QLabel()
        dot.setFixedSize(7, 7)
        dot.setStyleSheet(
            f"background:{dot_color}; border-radius:3px; border:none;"
        )
        status_lbl = QLabel(status if status else "—")
        status_lbl.setStyleSheet(
            f"color:{constants.TEXT_SEC}; font-size:9px;"
            f" background:transparent; border:none;"
        )
        s_row = QHBoxLayout()
        s_row.setContentsMargins(0, 0, 0, 0)
        s_row.setSpacing(3)
        s_row.addStretch()
        s_row.addWidget(dot, alignment=Qt.AlignVCenter)
        s_row.addWidget(status_lbl)
        s_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 4, 5, 4)
        layout.setSpacing(2)
        layout.addWidget(thumb_lbl, alignment=Qt.AlignCenter)
        layout.addWidget(ver_lbl)
        layout.addWidget(dept_lbl)
        layout.addWidget(date_lbl)
        layout.addLayout(s_row)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.version_clicked.emit(self._path)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.setStyleSheet(self._hover_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self._normal_style)
        super().leaveEvent(event)


class VersionHistoryPopup(QWidget):
    """Floating popup showing all versions of a SEQ asset as clickable cards."""
    version_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            f"background:{constants.BORDER};"
            f"border:1px solid {constants.SPLITTER_COLOR};"
            f"border-radius:8px;"
        )

        # Title bar
        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet(
            f"color:{constants.TEXT_SEC}; font-size:10px;"
            f" background:transparent; border:none; padding:0 4px;"
        )

        # Scroll area with horizontal strip of cards
        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("background:transparent; border:none;")
        self._scroll.setWidgetResizable(False)

        self._strip = QWidget()
        self._strip.setStyleSheet("background:transparent;")
        self._strip_layout = QHBoxLayout(self._strip)
        self._strip_layout.setContentsMargins(6, 4, 6, 4)
        self._strip_layout.setSpacing(6)
        self._scroll.setWidget(self._strip)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(4)
        outer.addWidget(self._title_lbl)
        outer.addWidget(self._scroll)

    def show_versions(self, asset_name: str, paths: list, global_pos: QPoint):
        """Populate cards and show the popup centred above *global_pos*."""
        # Remove old cards
        while self._strip_layout.count():
            child = self._strip_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        n = len(paths)
        plural = "s" if n != 1 else ""
        self._title_lbl.setText(f"  {asset_name}  —  {n} version{plural}")

        for p_str in paths:
            card = VersionCard(Path(p_str))
            card.version_clicked.connect(self._on_card_clicked)
            self._strip_layout.addWidget(card)

        # Size popup to fit cards (max ~6 visible; scroll for more)
        card_stride = VersionCard.CARD_W + 6
        strip_w     = n * card_stride + 12          # inner widget width
        visible_w   = min(strip_w, 6 * card_stride + 12)   # max 6 visible
        scroll_h    = VersionCard.CARD_H + 20       # card + scrollbar allowance

        self._strip.setFixedSize(strip_w, VersionCard.CARD_H + 8)
        self._scroll.setFixedSize(visible_w, scroll_h)
        self.adjustSize()

        # Position: centred above cursor; flip below if near top of screen
        screen = QApplication.desktop().screenGeometry(global_pos)
        w, h   = self.sizeHint().width(), self.sizeHint().height()
        x = global_pos.x() - w // 2
        y = global_pos.y() - h - 10
        x = max(screen.left() + 4, min(x, screen.right()  - w - 4))
        if y < screen.top() + 4:
            y = global_pos.y() + 24
        self.move(x, y)
        self.show()
        self.raise_()

    def _on_card_clicked(self, path: str):
        self.version_selected.emit(path)
        self.hide()


# ──────────────────────────────────────────────────────────────────────────── #
#  CenterPanel                                                                  #
# ──────────────────────────────────────────────────────────────────────────── #

class CenterPanel(QWidget):
    folder_changed    = pyqtSignal(str)
    items_loaded      = pyqtSignal(int)
    selection_changed = pyqtSignal(int)
    file_selected     = pyqtSignal(str)   # single file path, or "" if none/multi
    seq_item_selected = pyqtSignal(bool)  # True when selected item is SEQ-level
    artists_found     = pyqtSignal(list)  # unique artist names in the loaded folder
    filters_cleared   = pyqtSignal()      # emitted when the "Clear filters" button is clicked

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
        self._status_filter   = "All"
        self._status_locked   = True    # True until supervisor unlocks
        self._all_versions: dict = {}   # (canonical, ext) -> [Path, …] newest-first
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
        self.list_widget.setItemDelegate(StatusBadgeDelegate(self.list_widget))

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

        self._version_popup = VersionHistoryPopup()
        self._version_popup.version_selected.connect(self.file_selected)

        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.installEventFilter(self)   # keyboard nav

        self.list_widget.setMouseTracking(True)
        self.list_widget.viewport().setMouseTracking(True)
        self.list_widget.viewport().installEventFilter(self)

        # ── Empty / welcome state ────────────────────────────────────────
        self._empty_icon_lbl = QLabel()
        self._empty_icon_lbl.setAlignment(Qt.AlignHCenter)
        self._empty_icon_lbl.setStyleSheet("background: transparent;")

        self._empty_title_lbl = QLabel()
        self._empty_title_lbl.setAlignment(Qt.AlignHCenter)
        self._empty_title_lbl.setStyleSheet(
            f"background: transparent; color: {constants.TEXT_PRI};"
            f" font-size: 15px; font-weight: bold;"
        )

        self._empty_sub_lbl = QLabel()
        self._empty_sub_lbl.setAlignment(Qt.AlignHCenter)
        self._empty_sub_lbl.setWordWrap(True)
        self._empty_sub_lbl.setStyleSheet(
            f"background: transparent; color: {constants.TEXT_SEC}; font-size: 12px;"
        )

        self._clear_filters_btn = QPushButton("Clear filters")
        self._clear_filters_btn.setFixedWidth(120)
        self._clear_filters_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT};
                color: {constants.TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{ background-color: {constants.ACCENT_HI}; }}
        """)

    def create_layout(self):
        # Loading page — centred label shown while folder is being read
        loading_page = QWidget()
        lp_layout = QVBoxLayout(loading_page)
        lp_layout.addStretch()
        lp_layout.addWidget(self._loading_label)
        lp_layout.addStretch()

        # Empty / welcome page — centred message with optional clear button
        empty_page = QWidget()
        ep_layout  = QVBoxLayout(empty_page)
        ep_layout.setSpacing(6)
        ep_layout.addStretch(3)
        ep_layout.addWidget(self._empty_icon_lbl)
        ep_layout.addSpacing(8)
        ep_layout.addWidget(self._empty_title_lbl)
        ep_layout.addSpacing(4)
        ep_layout.addWidget(self._empty_sub_lbl)
        ep_layout.addSpacing(16)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._clear_filters_btn)
        btn_row.addStretch()
        ep_layout.addLayout(btn_row)
        ep_layout.addStretch(4)

        self._stack = QStackedWidget()
        self._stack.addWidget(loading_page)      # index 0 — loading
        self._stack.addWidget(self.list_widget)  # index 1 — content
        self._stack.addWidget(empty_page)        # index 2 — empty / welcome

        # Show welcome state on startup — no folder selected yet
        self._show_empty("folder.png", "No folder selected",
                         "Choose a catalog or browse to a folder to get started.",
                         show_clear=False)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self._stack)

    def create_connections(self):
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self._clear_filters_btn.clicked.connect(self._on_clear_filters)

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

        # ── Accessibility pre-check (non-blocking, 3 s timeout) ───────────
        ok, err_title, err_msg = self._check_path(path)
        if not ok:
            self._hide_loading()
            self._show_empty("cancel.png", err_title, err_msg,
                             show_clear=False, error=True)
            return

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

    def set_status_locked(self, locked: bool):
        """Enable or disable status editing in the context menu."""
        self._status_locked = locked

    def update_item_status(self, path: str, status: str):
        """Update the status badge for *path* without reloading the folder.

        Called when the right panel's status combo changes so the badge
        stays in sync immediately.
        """
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == path:
                item.setData(Qt.UserRole + 5, status)
                break
        self._apply_filters()
        self.list_widget.viewport().update()

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

    def filter_status(self, status: str):
        """Filter by pipeline status; pass ``'All'`` to show everything.
        Full implementation in step 5 — stub keeps the signal connection live."""
        self._status_filter = status
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
        # (canonical, ext)        -> [(ver_int, Path), …]  — ALL versions
        all_ver_dict: dict[tuple, list] = {}

        _scan_error: str = ""
        try:
            for root, dirs, files in os.walk(folder):
                dirs[:] = sorted(
                    [d for d in dirs if d != ".meta" and not is_excluded(d)],
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

                    # Collect every version for the history popup
                    _ver = version_key(p.stem)[1] or 0
                    all_ver_dict.setdefault(overall_key, []).append((_ver, p))
        except PermissionError as e:
            _scan_error = f"Permission denied — some files could not be read.\n{e}"
        except OSError as e:
            _scan_error = str(e)

        # If the scan failed entirely with no results, show the error and bail
        if _scan_error and not overall:
            self._hide_loading()
            self._show_empty("cancel.png", "Cannot read folder",
                             _scan_error, show_clear=False, error=True)
            return

        # Store all versions sorted newest-first for the history popup
        self._all_versions = {
            k: [p for _, p in sorted(v, key=lambda x: x[0], reverse=True)]
            for k, v in all_ver_dict.items()
        }

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
            item.setData(Qt.UserRole + 5, "")           # no badge at SEQ level
            self.list_widget.addItem(item)

        self._start_thumbnail_loader(thumbnail_paths, icon_size)
        self._hide_loading()
        self.items_loaded.emit(self.list_widget.count())
        self.artists_found.emit(sorted(artists))
        self._apply_filters()

    def _load_direct(self, folder: Path, icon_size: int):
        """Show immediate contents: subfolders first, then files."""
        self._all_versions = {}   # no version history in flat-folder view
        # Read all .meta files in this folder in one pass
        folder_meta = read_folder_meta(folder)

        thumbnail_paths = []
        artists: set[str] = set()
        _scan_error = ""
        try:
            entries = sorted(folder.iterdir(), key=self._entry_sort_key)
            for p in entries:
                # Hide .meta subfolder and any user-excluded patterns
                if p.is_dir() and (p.name == ".meta" or is_excluded(p.name)
                                   or not has_media_or_subfolders(str(p))):
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
                    item.setData(Qt.UserRole + 5, "")   # folders have no status
                    item.setIcon(colored_icon(constants.ACCENT, closed=True, size=icon_size))
                else:
                    meta = folder_meta.get(p.stem, {})
                    artist = meta.get("artist") or detect_artist(p.name)
                    if artist:
                        artists.add(artist)
                    item = self._make_file_item(p.stem, p, ext, icon_size, thumbnail_paths, meta)
                self.list_widget.addItem(item)
        except PermissionError as e:
            _scan_error = f"Permission denied — some files could not be read.\n{e}"
        except OSError as e:
            _scan_error = str(e)

        # If the scan failed entirely with no results, show the error and bail
        if _scan_error and self.list_widget.count() == 0:
            self._hide_loading()
            self._show_empty("cancel.png", "Cannot read folder",
                             _scan_error, show_clear=False, error=True)
            return

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
        # Status: from .meta file (empty string = no status set)
        item.setData(Qt.UserRole + 5, meta.get("status", ""))
        # Notes indicator: True if a .notes.json sidecar exists for this asset
        item.setData(Qt.UserRole + 6, has_notes(p))

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
            is_seq = selected[0].data(Qt.UserRole + 3) is not None
            self.seq_item_selected.emit(is_seq)
            self.file_selected.emit(selected[0].data(Qt.UserRole))
        else:
            self.seq_item_selected.emit(False)
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
            item_artist = (item.data(Qt.UserRole + 4) or "").lower()
            name_ok   = (not text) or (text in item.text().lower()) or (text in item_artist)
            asset_key = item.data(Qt.UserRole + 3)   # None for non-SEQ items

            status = self._status_filter

            if is_folder:
                dept_ok = artist_ok = status_ok = True
            elif asset_key is not None and asset_key in self._asset_versions:
                # SEQ item — swap path, never hide by dept/artist/status
                versions = self._asset_versions[asset_key]
                target   = versions.get(dept) if dept not in ("All", "") else None
                target   = target or versions.get("_overall")
                if target:
                    current_stored = item.data(Qt.UserRole)
                    new_path       = str(target)
                    item.setData(Qt.UserRole,     new_path)
                    item.setData(Qt.UserRole + 2, detect_department(target.name))
                    # Keep badge suppressed at SEQ level — never show status dot here
                    if current_stored != new_path:
                        item.setData(Qt.UserRole + 5, "")
                dept_ok = artist_ok = status_ok = True
            else:
                dept_ok   = dept   in ("All", "") or item.data(Qt.UserRole + 2) == dept
                artist_ok = artist in ("All", "") or item.data(Qt.UserRole + 4) == artist
                item_status = item.data(Qt.UserRole + 5) or ""
                if status in ("All", ""):
                    status_ok = True
                elif status == "No Status":
                    status_ok = item_status == ""
                else:
                    status_ok = item_status == status

            item.setHidden(not (name_ok and dept_ok and artist_ok and status_ok))

        self._update_empty_state()

    def _show_empty(self, icon_name: str, title: str, subtitle: str,
                    show_clear: bool, error: bool = False):
        """Switch to the empty-state page with the given message.

        *icon_name* is a filename (without path) from ``constants.ICONS_DIR``.
        Set *error* to True to render the title in the failure colour.
        """
        pix = QPixmap(str(constants.ICONS_DIR / icon_name))
        if not pix.isNull():
            self._empty_icon_lbl.setPixmap(
                pix.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            self._empty_icon_lbl.clear()

        title_color = constants.FAIL if error else constants.TEXT_PRI
        self._empty_title_lbl.setStyleSheet(
            f"background: transparent; color: {title_color};"
            f" font-size: 15px; font-weight: bold;"
        )
        self._empty_title_lbl.setText(title)
        self._empty_sub_lbl.setText(subtitle)
        self._clear_filters_btn.setVisible(show_clear)
        self._stack.setCurrentIndex(2)

    def _check_path(self, path: str, timeout: float = 3.0) -> tuple:
        """Return ``(ok, title, message)`` — never blocks the main thread longer than *timeout* s.

        Runs ``Path.exists() / is_dir()`` in a daemon thread so an unreachable
        network mount doesn't freeze the UI while the OS times out.
        """
        result = [True, "", ""]

        def _probe():
            p = Path(path)
            try:
                if not p.exists():
                    result[0] = False
                    result[1] = "Folder not found"
                    result[2] = f"This folder no longer exists:\n{path}"
                elif not p.is_dir():
                    result[0] = False
                    result[1] = "Not a folder"
                    result[2] = f"This path is not a folder:\n{path}"
            except PermissionError:
                result[0] = False
                result[1] = "Permission denied"
                result[2] = f"You don't have permission to access:\n{path}"
            except OSError as e:
                result[0] = False
                result[1] = "Cannot access folder"
                result[2] = str(e)

        t = threading.Thread(target=_probe, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            return (
                False,
                "Network path unreachable",
                f"No response after {timeout:.0f} s — the share may be offline:\n{path}",
            )

        return tuple(result)

    def _update_empty_state(self):
        """After filtering, decide whether to show content or an empty message."""
        total   = self.list_widget.count()
        visible = sum(
            1 for i in range(total)
            if not self.list_widget.item(i).isHidden()
        )

        if visible > 0:
            self._stack.setCurrentIndex(1)
            return

        filters_active = (
            bool(self._text_filter)
            or self._dept_filter   not in ("All", "")
            or self._artist_filter not in ("All", "")
            or self._status_filter not in ("All", "")   # includes "No Status"
        )

        if total == 0:
            # Folder loaded but contained no matching files
            self._show_empty(
                "open-file.png",
                "Folder is empty",
                "No supported files were found here.",
                show_clear=False,
            )
        elif filters_active:
            # Files exist but all hidden by active filters
            self._show_empty(
                "search.png",
                "No results",
                "No files match your current filters.",
                show_clear=True,
            )
        else:
            # Shouldn't normally reach here, but guard anyway
            self._stack.setCurrentIndex(1)

    def _on_clear_filters(self):
        """Reset all internal filters, reload, and notify the header."""
        self._text_filter   = ""
        self._dept_filter   = "All"
        self._artist_filter = "All"
        self._status_filter = "All"
        self.filters_cleared.emit()          # header widget resets its combos
        if self.current_path:
            self.load_folder(self.current_path)

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

            # Version History — only for SEQ items (UserRole+3 set)
            asset_key = item.data(Qt.UserRole + 3)
            if asset_key is not None and asset_key in self._all_versions:
                hist_pos = self.list_widget.viewport().mapToGlobal(pos)
                history_act = menu.addAction("Version History")
                history_act.triggered.connect(
                    lambda *_, k=asset_key, gp=hist_pos:
                        self._show_version_history(k, gp)
                )
                menu.addSeparator()

            copy_path_act = menu.addAction("Copy Path")
            copy_path_act.triggered.connect(lambda: self._copy_to_clipboard(path))

            copy_name_act = menu.addAction("Copy Name")
            copy_name_act.triggered.connect(
                lambda: self._copy_to_clipboard(Path(path).name)
            )

            if not is_folder:
                notes_act = menu.addAction("Notes")
                notes_act.triggered.connect(
                    lambda *_, p=path: self._show_notes_dialog(p)
                )

            if not is_folder:
                ext = Path(path).suffix.lower()
                if ext in constants.VIDEO_EXTS:
                    menu.addSeparator()
                    player_act = menu.addAction("Open in BlastPlayer")
                    player_act.triggered.connect(lambda: self._open_in_blast_player(path))

                # ── Submit for Review (all users, not SEQ level) ─────────
                is_seq = asset_key is not None
                if not is_seq:
                    menu.addSeparator()
                    submit_act = menu.addAction("Submit for Review")
                    current_status = item.data(Qt.UserRole + 5) or ""
                    submit_act.setEnabled(current_status != "Approved")
                    submit_act.triggered.connect(
                        lambda *_, p=path: self._submit_for_review([p])
                    )

                # ── Set Status submenu (supervisor only, not SEQ level) ──
                if not self._status_locked and not is_seq:
                    menu.addSeparator()
                    status_menu = menu.addMenu("Set Status")
                    for _s in constants.STATUS_OPTIONS:
                        _act = status_menu.addAction(_s)
                        _act.triggered.connect(
                            lambda *_, s=_s: self._set_status([path], s)
                        )
                    status_menu.addSeparator()
                    clear_act = status_menu.addAction("Clear Status")
                    clear_act.triggered.connect(lambda: self._set_status([path], ""))

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

            # Exclude folders (UserRole+1) and SEQ items (UserRole+3)
            file_paths = [
                it.data(Qt.UserRole)
                for it in items
                if not it.data(Qt.UserRole + 1)       # exclude folders
                and it.data(Qt.UserRole + 3) is None  # exclude SEQ items
            ]

            # Submit for Review — all users, skip Approved
            submittable = [
                it.data(Qt.UserRole) for it in items
                if not it.data(Qt.UserRole + 1)
                and it.data(Qt.UserRole + 3) is None
                and (it.data(Qt.UserRole + 5) or "") != "Approved"
            ]
            if submittable:
                menu.addSeparator()
                submit_act = menu.addAction(f"Submit for Review  ({len(submittable)} files)")
                submit_act.triggered.connect(
                    lambda *_, sp=submittable: self._submit_for_review(sp)
                )

            # Set Status for all selected *files* — supervisor only
            if file_paths and not self._status_locked:
                menu.addSeparator()
                status_menu = menu.addMenu(f"Set Status  ({len(file_paths)} files)")
                for _s in constants.STATUS_OPTIONS:
                    _act = status_menu.addAction(_s)
                    _act.triggered.connect(
                        lambda *_, s=_s: self._set_status(file_paths, s)
                    )
                status_menu.addSeparator()
                clear_act = status_menu.addAction("Clear Status")
                clear_act.triggered.connect(lambda: self._set_status(file_paths, ""))

        menu.exec_(self.list_widget.viewport().mapToGlobal(pos))

    def _show_version_history(self, asset_key: tuple, global_pos: QPoint):
        """Open the version history popup for *asset_key* near *global_pos*."""
        paths = self._all_versions.get(asset_key, [])
        if len(paths) < 1:
            return
        can = asset_key[0]
        self._version_popup.show_versions(can, [str(p) for p in paths], global_pos)

    def _show_notes_dialog(self, path: str):
        """Open the notes dialog for *path* and refresh its notes indicator on close."""
        from dialogs.notes_dialog import NotesDialog
        dlg = NotesDialog(path, parent=self)
        dlg.exec_()
        # Refresh the notes dot in case a note was just added
        updated = has_notes(path)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == path:
                item.setData(Qt.UserRole + 6, updated)
                break
        self.list_widget.viewport().update()

    def _copy_to_clipboard(self, text: str):
        QApplication.clipboard().setText(text)

    def _submit_for_review(self, paths: list):
        """Set status to 'Review' for *paths*, skipping any already Approved."""
        eligible = []
        path_set = set(paths)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) in path_set:
                if (item.data(Qt.UserRole + 5) or "") != "Approved":
                    eligible.append(item.data(Qt.UserRole))
        if eligible:
            self._set_status(eligible, "Review")

    def _set_status(self, paths: list, status: str):
        """Write *status* to each file in *paths* and refresh the badge.

        *paths* is a list of absolute path strings captured at menu-build
        time — never QListWidgetItem references, which can be deleted by a
        folder reload while the context menu is still open.

        *status* is one of STATUS_OPTIONS, or ``""`` to clear.
        """
        path_set = set(paths)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            p_str = item.data(Qt.UserRole)
            if p_str not in path_set:
                continue
            p = Path(p_str)
            try:
                data = read_meta(p)
                if status:
                    data["status"] = status
                else:
                    data.pop("status", None)
                write_meta(p, data)
                item.setData(Qt.UserRole + 5, status)
            except Exception as e:
                print(f"[CenterPanel] Could not set status for {p.name}: {e}")
        # Re-run filters so "No Status" / specific-status filters update live
        self._apply_filters()
        # Force the delegate to repaint every visible item — Qt does not
        # automatically redraw for custom UserRole changes.
        self.list_widget.viewport().update()
        # If the right panel is showing one of the changed files, refresh it
        selected = self.list_widget.selectedItems()
        if len(selected) == 1 and selected[0].data(Qt.UserRole) in path_set:
            self.file_selected.emit(selected[0].data(Qt.UserRole))

    def _open_in_blast_player(self, path: str):
        """Launch BlastPlayer in a separate process with *path* pre-loaded."""
        player = constants.BLAST_PLAYER_PATH
        if not player.is_file():
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "BlastPlayer not found",
                f"Could not locate BlastPlayer at:\n{player}\n\n"
                "Check that BlastPlayer is installed alongside BlastVault."
            )
            return
        try:
            subprocess.Popen([sys.executable, str(player), path])
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Launch failed", str(e))

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
