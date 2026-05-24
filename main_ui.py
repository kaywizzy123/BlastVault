import os
import sys
import json
import fnmatch
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

STUDIO_NAME = "NEON ANIMATION STUDIOS"
ROOT_DIR = r"C:\SHOWS"
ICON = r".\icons\bv.png"
CONFIG_PATH = r".\config.json"

BG = "#0a0a0a"
BORDER = "#262626"
ACCENT_HI = "#1085d3"
ACCENT = "#0a5b91"
TEXT_PRI = "#ededed"
TEXT_SEC = "#a1a1a1"
FAIL = "#ad0303"
SUCCESS = "#03ad14"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"}
DOC_EXTS   = {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx"}
AUDIO_EXTS = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".aiff", ".m4a"}
OBJ_3D_EXTS = {".fbx", ".usd", ".usda", ".usdc", ".usdz"}

ALLOWED_EXTS = IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS | OBJ_3D_EXTS | DOC_EXTS

EXCLUDED_PATTERNS = []


def load_config():
    global EXCLUDED_PATTERNS
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
                EXCLUDED_PATTERNS = data.get("excluded_patterns", [])
                return data.get("catalogs", [])
        except Exception:
            EXCLUDED_PATTERNS = []
    return []


def save_config(catalog_paths=None):
    try:
        existing = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                existing = json.load(f)
        existing["excluded_patterns"] = EXCLUDED_PATTERNS
        if catalog_paths is not None:
            existing["catalogs"] = catalog_paths
        with open(CONFIG_PATH, "w") as f:
            json.dump(existing, f, indent=2)
    except Exception:
        pass


def is_excluded(name):
    for pattern in EXCLUDED_PATTERNS:
        if fnmatch.fnmatch(name.lower(), pattern.lower()):
            return True
    return False


styleSheet = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT_PRI};
}}
QMenuBar {{
    background-color: {BORDER};
    color: {TEXT_PRI};
}}
QMenuBar::item:selected {{
    background-color: {ACCENT};
}}
QMenu {{
    background-color: {BORDER};
    border: 1px solid {BORDER};
}}
QMenu::item {{
    padding: 6px 20px;
    background-color: transparent;
}}
QMenu::item:selected {{
    background-color: {ACCENT};
    color: {TEXT_PRI};
}}
QSplitter::handle {{
    background-color: {BORDER};
}}
QSplitter::handle:horizontal {{
    width: 4px;
}}
HeaderWidget {{
    background-color: {BORDER};
}}
LeftPanel {{
    background-color: {BG};
}}
CenterPanel {{
    background-color: {BG};
}}
RightPanel {{
    background-color: {BG};
}}
QTreeWidget {{
    background-color: {BG};
    color: {TEXT_PRI};
    border: none;
    outline: none;
}}
QTreeWidget::item {{
    padding: 4px 8px;
    border: none;
}}
QTreeWidget::item:hover {{
    background-color: {BORDER};
    color: {TEXT_PRI};
}}
QTreeWidget::item:selected {{
    background-color: {ACCENT};
    color: {TEXT_PRI};
}}
QTreeWidget::branch {{
    background-color: {BG};
}}
QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:closed:has-children:has-siblings {{
    image: none;
    border-image: none;
}}
QTreeWidget::branch:open:has-children:!has-siblings,
QTreeWidget::branch:open:has-children:has-siblings {{
    image: none;
    border-image: none;
}}
QHeaderView::section {{
    background-color: {BORDER};
    color: {TEXT_SEC};
    border: none;
    padding: 4px 8px;
}}
QListWidget {{
    background-color: {BG};
    color: {TEXT_PRI};
    border: none;
    outline: none;
}}
QListWidget::item {{
    border: none;
    padding: 2px;
}}
QListWidget::item:hover {{
    background-color: {BORDER};
}}
QListWidget::item:selected {{
    background-color: {ACCENT};
    color: {TEXT_PRI};
}}
QScrollBar:vertical {{
    background-color: {BG};
    width: 8px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: {BORDER};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {ACCENT};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background-color: {BG};
    height: 8px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background-color: {BORDER};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {ACCENT};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""


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
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXTS:
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            return QIcon(pixmap.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        return make_placeholder_icon(BORDER, icon_size, "IMG")
    elif ext in VIDEO_EXTS:
        return make_placeholder_icon("#1a1a2e", icon_size, "\u25b6")
    elif ext in AUDIO_EXTS:
        return make_placeholder_icon("#2e1a2e", icon_size, "\u266b")
    elif ext in OBJ_3D_EXTS:
        return make_placeholder_icon("#2e2a1a", icon_size, "\u25c6")
    elif ext in DOC_EXTS:
        return make_placeholder_icon("#1a2e1a", icon_size, "\u2750")
    else:
        return make_placeholder_icon(BORDER, icon_size, "\u2022")


def header_btn_style():
    return f"""
        QPushButton {{
            background-color: transparent;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {ACCENT};
            border-radius: 4px;
        }}
    """


def context_menu_style():
    return f"""
        QMenu {{
            background-color: {BORDER};
            border: 1px solid {ACCENT};
        }}
        QMenu::item {{
            padding: 6px 20px;
            color: {TEXT_PRI};
        }}
        QMenu::item:selected {{
            background-color: {ACCENT};
        }}
    """


def dialog_list_style():
    return f"""
        QListWidget {{
            background-color: {BG};
            color: {TEXT_PRI};
            border: 1px solid {BORDER};
            border-radius: 4px;
            outline: none;
        }}
        QListWidget::item {{
            padding: 6px 8px;
            border: none;
        }}
        QListWidget::item:hover {{
            background-color: {BORDER};
        }}
        QListWidget::item:selected {{
            background-color: {ACCENT};
        }}
    """


def input_style():
    return f"""
        QLineEdit {{
            background-color: {BORDER};
            color: {TEXT_PRI};
            border: 1px solid {BORDER};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QLineEdit:focus {{
            border: 1px solid {ACCENT};
        }}
    """


class SettingsDialog(QDialog):
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(500, 550)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.section_label = QLabel("Excluded Folder Patterns")
        self.section_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {TEXT_PRI};
            background: transparent;
        """)

        self.hint_label = QLabel(
            "Folders matching these patterns will be hidden.\n"
            "Supports wildcards: * (any chars), ? (single char)\n"
            "Examples: _archive, backup*, *.tmp, .hidden"
        )
        self.hint_label.setStyleSheet(f"""
            font-size: 11px;
            color: {TEXT_SEC};
            background: transparent;
        """)

        self.pattern_list = QListWidget()
        self.pattern_list.setStyleSheet(dialog_list_style())
        self.pattern_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.populate_list()

        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("Enter pattern (e.g. _archive, backup*)")
        self.pattern_input.setStyleSheet(input_style())

        self.add_btn = QPushButton("Add")
        self.add_btn.setFixedWidth(80)
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                color: {TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_HI};
            }}
        """)

        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {FAIL};
                color: {TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT};
            }}
        """)

        self.save_btn = QPushButton("Save")
        self.save_btn.setFixedWidth(100)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                color: {TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_HI};
            }}
        """)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BORDER};
                color: {TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT};
            }}
        """)

    def populate_list(self):
        self.pattern_list.clear()
        for pattern in EXCLUDED_PATTERNS:
            item = QListWidgetItem(pattern)
            self.pattern_list.addItem(item)

    def create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        main_layout.addWidget(self.section_label)
        main_layout.addWidget(self.hint_label)
        main_layout.addWidget(self.pattern_list)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.pattern_input)
        input_layout.addWidget(self.add_btn)
        main_layout.addLayout(input_layout)

        main_layout.addWidget(self.remove_btn)
        main_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        main_layout.addLayout(btn_layout)

    def create_connections(self):
        self.add_btn.clicked.connect(self.on_add)
        self.remove_btn.clicked.connect(self.on_remove)
        self.save_btn.clicked.connect(self.on_save)
        self.cancel_btn.clicked.connect(self.reject)
        self.pattern_input.returnPressed.connect(self.on_add)

    def on_add(self):
        text = self.pattern_input.text().strip()
        if not text:
            return
        if text not in EXCLUDED_PATTERNS:
            self.pattern_list.addItem(QListWidgetItem(text))
        self.pattern_input.clear()

    def on_remove(self):
        for item in self.pattern_list.selectedItems():
            self.pattern_list.takeItem(self.pattern_list.row(item))

    def on_save(self):
        global EXCLUDED_PATTERNS
        EXCLUDED_PATTERNS = [
            self.pattern_list.item(i).text()
            for i in range(self.pattern_list.count())
        ]
        save_config()
        self.settings_changed.emit()
        self.accept()


class AddCatalogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Catalog")
        self.setFixedSize(400, 500)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.selected_paths = []
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search...")
        self.search_box.setStyleSheet(input_style())

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(dialog_list_style())
        self.populate_list()

        self.confirm_btn = QPushButton("Add Selected")
        self.confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                color: {TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_HI};
            }}
        """)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BORDER};
                color: {TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT};
            }}
        """)

    def populate_list(self, filter_text=""):
        self.list_widget.clear()
        if not os.path.exists(ROOT_DIR):
            return
        try:
            for entry in sorted(os.scandir(ROOT_DIR), key=lambda e: e.name.lower()):
                if entry.is_dir() and not is_excluded(entry.name):
                    if filter_text.lower() in entry.name.lower():
                        item = QListWidgetItem(entry.name)
                        item.setData(Qt.UserRole, entry.path)
                        item.setCheckState(Qt.Unchecked)
                        item.setIcon(colored_icon(ACCENT, closed=True))
                        self.list_widget.addItem(item)
        except PermissionError:
            pass

    def create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)
        main_layout.addWidget(self.search_box)
        main_layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.confirm_btn)
        main_layout.addLayout(btn_layout)

    def create_connections(self):
        self.confirm_btn.clicked.connect(self.on_confirm)
        self.cancel_btn.clicked.connect(self.reject)
        self.search_box.textChanged.connect(self.populate_list)

    def on_confirm(self):
        self.selected_paths = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                self.selected_paths.append(item.data(Qt.UserRole))
        self.accept()


class RemoveCatalogDialog(QDialog):
    def __init__(self, tree_root, folder_closed_icon, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Remove Catalog")
        self.setFixedSize(400, 500)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.tree_root = tree_root
        self.folder_closed_icon = folder_closed_icon
        self.items_to_remove = []
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search...")
        self.search_box.setStyleSheet(input_style())

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(dialog_list_style())
        self.list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
        self.populate_list()

        self.confirm_btn = QPushButton("Remove Selected")
        self.confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {FAIL};
                color: {TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT};
            }}
        """)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BORDER};
                color: {TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT};
            }}
        """)

    def populate_list(self, filter_text=""):
        self.list_widget.clear()
        for i in range(self.tree_root.childCount()):
            tree_item = self.tree_root.child(i)
            if filter_text.lower() in tree_item.text(0).lower():
                list_item = QListWidgetItem(tree_item.text(0))
                list_item.setData(Qt.UserRole, tree_item)
                list_item.setIcon(self.folder_closed_icon)
                self.list_widget.addItem(list_item)

    def create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)
        main_layout.addWidget(self.search_box)
        main_layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.confirm_btn)
        main_layout.addLayout(btn_layout)

    def create_connections(self):
        self.confirm_btn.clicked.connect(self.on_confirm)
        self.cancel_btn.clicked.connect(self.reject)
        self.search_box.textChanged.connect(self.populate_list)

    def on_confirm(self):
        self.items_to_remove = [
            item.data(Qt.UserRole)
            for item in self.list_widget.selectedItems()
        ]
        self.accept()


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About BlastVault")
        self.setFixedSize(500, 300)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.title_label = QLabel("BlastVault v1.0")
        self.title_label.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {TEXT_PRI};
            background: transparent;
        """)
        self.title_label.setAlignment(Qt.AlignCenter)

        self.desc_label = QLabel("This app was designed and developed by\nOluwakayode Ogunremi\n\u00a92026")
        self.desc_label.setStyleSheet(f"""
            font-size: 13px;
            color: {TEXT_SEC};
            background: transparent;
        """)
        self.desc_label.setAlignment(Qt.AlignCenter)

        self.close_button = QPushButton("Close")
        self.close_button.setFixedWidth(100)
        self.close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {BORDER};
                color: {TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT};
            }}
        """)
        self.close_button.clicked.connect(self.close)

    def create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)
        main_layout.addStretch()
        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.desc_label)
        main_layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)


class ThumbnailLoader(QThread):
    thumbnail_ready = pyqtSignal(str, QIcon)

    def __init__(self, tasks, icon_size):
        super().__init__()
        self.tasks = tasks
        self.icon_size = icon_size

    def run(self):
        for path in self.tasks:
            icon = get_file_icon(path, self.icon_size)
            self.thumbnail_ready.emit(path, icon)


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
        self.list_widget.setIconSize(QSize(120, 120))
        self.list_widget.setGridSize(QSize(140, 160))
        self.list_widget.setWordWrap(True)
        self.list_widget.setSpacing(2)
        self.list_widget.setResizeMode(QListWidget.Adjust)

    def create_layout(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.list_widget)

    def create_connections(self):
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

    def load_folder(self, path):
        self.current_path = path
        self.list_widget.clear()

        if self.thumbnail_loader and self.thumbnail_loader.isRunning():
            self.thumbnail_loader.terminate()
            self.thumbnail_loader.wait()

        icon_size = 120 if self.is_grid_view else 48
        entries = []

        try:
            for entry in sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower())):
                if entry.is_dir() and is_excluded(entry.name):
                    continue

                ext = os.path.splitext(entry.name)[1].lower()
                if not entry.is_dir() and ext not in ALLOWED_EXTS:
                    continue

                item = QListWidgetItem(entry.name)
                item.setData(Qt.UserRole, entry.path)
                item.setData(Qt.UserRole + 1, entry.is_dir())

                if entry.is_dir():
                    item.setIcon(colored_icon(ACCENT, closed=True, size=icon_size))
                    self.list_widget.addItem(item)
                else:
                    if ext in IMAGE_EXTS:
                        item.setIcon(make_placeholder_icon(BORDER, icon_size, "..."))
                        entries.append(entry.path)
                    else:
                        item.setIcon(get_file_icon(entry.path, icon_size))
                    self.list_widget.addItem(item)
        except PermissionError:
            pass

        if entries:
            self.thumbnail_loader = ThumbnailLoader(entries, icon_size)
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
            self.list_widget.setIconSize(QSize(120, 120))
            self.list_widget.setGridSize(QSize(140, 160))
            self.list_widget.setWordWrap(True)
        else:
            self.list_widget.setViewMode(QListWidget.ListMode)
            self.list_widget.setIconSize(QSize(48, 48))
            self.list_widget.setGridSize(QSize())
        if self.current_path:
            self.load_folder(self.current_path)


class LeftPanel(QWidget):
    folder_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.folder_closed = colored_icon(ACCENT, closed=True)
        self.folder_open = colored_icon(ACCENT, closed=False)
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.tree_widget = QTreeWidget()
        self.tree_widget.header().hide()
        self.tree_widget.setColumnCount(1)
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)

    def create_layout(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.tree_widget)

    def create_connections(self):
        self.tree_widget.itemExpanded.connect(self.on_item_expanded)
        self.tree_widget.itemCollapsed.connect(self.on_item_collapsed)
        self.tree_widget.itemClicked.connect(self.on_item_clicked)
        self.tree_widget.customContextMenuRequested.connect(self.on_context_menu)

    def add_catalog(self):
        dialog = AddCatalogDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            for path in dialog.selected_paths:
                root_item = QTreeWidgetItem(self.tree_widget, [QDir(path).dirName()])
                root_item.setData(0, Qt.UserRole, path)
                root_item.setIcon(0, self.folder_closed)
                self.add_children(root_item, path)

    def remove_catalog(self):
        root = self.tree_widget.invisibleRootItem()
        if root.childCount() == 0:
            return
        dialog = RemoveCatalogDialog(root, self.folder_closed, self)
        if dialog.exec_() == QDialog.Accepted:
            for tree_item in dialog.items_to_remove:
                root.removeChild(tree_item)

    def refresh_all(self):
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            catalog = root.child(i)
            while catalog.childCount():
                catalog.removeChild(catalog.child(0))
            self.add_children(catalog, catalog.data(0, Qt.UserRole))

    def add_children(self, parent_item, path):
        directory = QDir(path)
        directory.setFilter(QDir.Dirs | QDir.NoDotAndDotDot)
        directory.setSorting(QDir.Name)

        for folder in directory.entryInfoList():
            if is_excluded(folder.fileName()):
                continue
            child = QTreeWidgetItem(parent_item, [folder.fileName()])
            child.setData(0, Qt.UserRole, folder.absoluteFilePath())
            child.setIcon(0, self.folder_closed)
            if QDir(folder.absoluteFilePath()).entryInfoList(
                QDir.Dirs | QDir.NoDotAndDotDot
            ):
                QTreeWidgetItem(child, [""])

    def on_item_clicked(self, item):
        path = item.data(0, Qt.UserRole)
        if path:
            self.folder_selected.emit(path)

    def sync_to_path(self, path):
        root = self.tree_widget.invisibleRootItem()
        self._find_and_select(root, path)

    def _find_and_select(self, parent, path):
        for i in range(parent.childCount()):
            item = parent.child(i)
            if item.data(0, Qt.UserRole) == path:
                self.tree_widget.setCurrentItem(item)
                self.tree_widget.scrollToItem(item)
                p = item.parent()
                while p:
                    self.tree_widget.expandItem(p)
                    p = p.parent()
                return True
            if self._find_and_select(item, path):
                return True
        return False

    def on_context_menu(self, pos):
        item = self.tree_widget.itemAt(pos)
        menu = QMenu(self)
        menu.setStyleSheet(context_menu_style())

        add_action = menu.addAction("Add Catalog")
        remove_action = None
        if item and item.parent() is None:
            remove_action = menu.addAction("Remove Catalog")

        action = menu.exec_(self.tree_widget.viewport().mapToGlobal(pos))

        if action == add_action:
            self.add_catalog()
        elif remove_action and action == remove_action:
            self.tree_widget.invisibleRootItem().removeChild(item)
            self.save_catalogs()

    def on_item_collapsed(self, item):
        item.setIcon(0, self.folder_closed)

    def on_item_expanded(self, item):
        item.setIcon(0, self.folder_open)
        for i in range(item.childCount()):
            child = item.child(i)
            if child.text(0) == "":
                item.removeChild(child)
                break
        if item.childCount() == 0:
            self.add_children(item, item.data(0, Qt.UserRole))
            
    def get_catalog_paths(self):
        root = self.tree_widget.invisibleRootItem()
        return [
            root.child(i).data(0, Qt.UserRole)
            for i in range(root.childCount())
        ]

    def save_catalogs(self):
        save_config(catalog_paths=self.get_catalog_paths())

    def add_catalog(self):
        dialog = AddCatalogDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            for path in dialog.selected_paths:
                self._add_catalog_item(path)
            self.save_catalogs()

    def remove_catalog(self):
        root = self.tree_widget.invisibleRootItem()
        if root.childCount() == 0:
            return
        dialog = RemoveCatalogDialog(root, self.folder_closed, self)
        if dialog.exec_() == QDialog.Accepted:
            for tree_item in dialog.items_to_remove:
                root.removeChild(tree_item)
            self.save_catalogs()

    def _add_catalog_item(self, path):
        if not os.path.exists(path):
            return
        root_item = QTreeWidgetItem(self.tree_widget, [QDir(path).dirName()])
        root_item.setData(0, Qt.UserRole, path)
        root_item.setIcon(0, self.folder_closed)
        self.add_children(root_item, path)

    def restore_catalogs(self, paths):
        for path in paths:
            self._add_catalog_item(path)


class RightPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        pass

    def create_layout(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

    def create_connections(self):
        pass


class HeaderWidget(QWidget):
    toggle_view = pyqtSignal()
    search_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(40)
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.studio_label = QLabel(STUDIO_NAME)
        self.studio_label.setStyleSheet(
            f"background:transparent; font-size: 16px; font-weight: bold; "
            f"color: {ACCENT_HI}; letter-spacing: 2px;"
        )

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.setFixedWidth(300)
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG};
                color: {TEXT_PRI};
                border: 1px solid {BORDER};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QLineEdit:focus {{
                border: 1px solid {ACCENT};
            }}
        """)

        self.filter_btn = QPushButton()
        self.filter_btn.setIcon(QIcon(r".\icons\dashboards.png"))
        self.filter_btn.setFixedSize(28, 28)
        self.filter_btn.setIconSize(QSize(20, 20))
        self.filter_btn.setCheckable(True)
        self.filter_btn.setChecked(True)
        self.filter_btn.setStyleSheet(header_btn_style())

        self.refresh_btn = QPushButton()
        self.refresh_btn.setIcon(QIcon(r".\icons\refresh.png"))
        self.refresh_btn.setFixedSize(28, 28)
        self.refresh_btn.setIconSize(QSize(20, 20))
        self.refresh_btn.setStyleSheet(header_btn_style())

    def create_layout(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 0, 10, 0)
        self.main_layout.setSpacing(6)
        self.main_layout.addWidget(self.studio_label)
        self.main_layout.addStretch()
        self.main_layout.addWidget(self.search_bar)
        self.main_layout.addWidget(self.filter_btn)
        self.main_layout.addWidget(self.refresh_btn)

    def create_connections(self):
        self.filter_btn.clicked.connect(self.on_toggle_view)
        self.refresh_btn.clicked.connect(self.on_refresh)
        self.search_bar.textChanged.connect(self.search_changed)

    def on_toggle_view(self):
        if self.filter_btn.isChecked():
            self.filter_btn.setIcon(QIcon(r".\icons\dashboards.png"))
        else:
            self.filter_btn.setIcon(QIcon(r".\icons\grid.png"))
        self.toggle_view.emit()

    def on_refresh(self):
        pass


class MainWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setWindowTitle("BlastVault")
        self.setMinimumSize(1920, 1080)
        self.setStyleSheet(styleSheet)
        self.setWindowIcon(QIcon(ICON))

        saved_catalogs = load_config()
        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.left_panel.restore_catalogs(saved_catalogs)

    def create_widgets(self):
        self.menu_bar = QMenuBar()
        menu_menu = self.menu_bar.addMenu("Menu")
        self.add_catalog_action = menu_menu.addAction("Add Catalog")
        self.remove_catalog_action = menu_menu.addAction("Remove Catalog")

        options_menu = self.menu_bar.addMenu("Options")
        self.settings_action = options_menu.addAction("Settings")
        self.about_action = options_menu.addAction("About")

        self.header_widget = HeaderWidget()

        self.splitter = QSplitter(Qt.Horizontal)

        self.left_panel = LeftPanel()
        self.center_panel = CenterPanel()
        self.right_panel = RightPanel()

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.center_panel)
        self.splitter.addWidget(self.right_panel)

        self.splitter.setSizes([384, 1152, 384])
        self.splitter.setStretchFactor(0, 20)
        self.splitter.setStretchFactor(1, 60)
        self.splitter.setStretchFactor(2, 20)

    def create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setMenuBar(self.menu_bar)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.header_widget)
        main_layout.addWidget(self.splitter)

    def create_connections(self):
        self.about_action.triggered.connect(self.show_about)
        self.settings_action.triggered.connect(self.show_settings)
        self.add_catalog_action.triggered.connect(self.left_panel.add_catalog)
        self.remove_catalog_action.triggered.connect(self.left_panel.remove_catalog)
        self.left_panel.folder_selected.connect(self.on_folder_selected)
        self.center_panel.folder_changed.connect(self.left_panel.sync_to_path)
        self.header_widget.toggle_view.connect(self.center_panel.toggle_view)
        self.header_widget.search_changed.connect(self.center_panel.filter_items)
        self.header_widget.refresh_btn.clicked.connect(self.on_refresh)

    def on_folder_selected(self, path):
        self.header_widget.search_bar.clear()
        self.center_panel.load_folder(path)

    def on_refresh(self):
        if self.center_panel.current_path:
            self.header_widget.search_bar.clear()
            self.center_panel.load_folder(self.center_panel.current_path)

    def show_about(self):
        dialog = AboutDialog(self)
        dialog.exec_()

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self.on_settings_changed)
        dialog.exec_()

    def on_settings_changed(self):
        self.left_panel.refresh_all()
        if self.center_panel.current_path:
            self.center_panel.load_folder(self.center_panel.current_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())