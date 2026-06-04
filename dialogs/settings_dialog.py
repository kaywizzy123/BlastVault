import sys
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QHBoxLayout, QAbstractItemView,
    QFileDialog, QTabWidget, QWidget, QFrame,
)
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon

from core import constants
from core.config import save_config, export_config, import_config
from core.styles import dialog_list_style, input_style


class SettingsDialog(QDialog):
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        if constants.can_admin():
            self.setFixedSize(520, 620)
        else:
            self.setFixedSize(400, 140)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    # ------------------------------------------------------------------ #
    #  Widget construction                                                 #
    # ------------------------------------------------------------------ #

    def create_widgets(self):
        # ── General tab ─────────────────────────────────────────────────
        self.user_name_label    = QLabel("Your Name:")
        self.user_name_lineEdit = QLineEdit()
        self.user_name_lineEdit.setText(constants.CURRENT_USER)
        self.user_name_lineEdit.setPlaceholderText("e.g.  oogunremi")
        self.user_name_lineEdit.setStyleSheet(self._input_style())

        self.save_btn = QPushButton("Save")
        self.save_btn.setFixedWidth(100)
        self.save_btn.setStyleSheet(self._btn_style(hover_color=constants.ACCENT_HI))

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.setStyleSheet(self._btn_style(hover_color=constants.FAIL))

        # Non-admin: only needs name + action buttons — skip all admin widgets
        if not constants.can_admin():
            return

        self.studio_name_label    = QLabel("Studio Name:")
        self.studio_name_lineEdit = QLineEdit()
        self.studio_name_lineEdit.setText(constants.STUDIO_NAME)
        self.studio_name_lineEdit.setStyleSheet(self._input_style())

        self.studio_root_label    = QLabel("Studio Root:")
        self.studio_root_lineEdit = QLineEdit()
        self.studio_root_lineEdit.setText(constants.ROOT_DIR)
        _root_hint = (
            r"e.g.  Z:\SHOWS  or  \\server\shows" if sys.platform == "win32"
            else "e.g.  /Volumes/server/shows  or  ~/Shows" if sys.platform == "darwin"
            else "e.g.  /mnt/server/shows  or  ~/shows"
        )
        self.studio_root_lineEdit.setPlaceholderText(_root_hint)
        self.studio_root_lineEdit.setStyleSheet(self._input_style())

        self.studio_root_browse_btn = QPushButton()
        self.studio_root_browse_btn.setIcon(QIcon(str(constants.ICONS_DIR / "folder.png")))
        self.studio_root_browse_btn.setIconSize(QSize(12, 12))
        self.studio_root_browse_btn.setStyleSheet(self._btn_style())

        self.section_label = QLabel("Excluded Folder Patterns")
        self.section_label.setStyleSheet(self._section_style())

        self.hint_label = QLabel(
            "Folders matching these patterns will be hidden.\n"
            "Supports wildcards: * (any chars), ? (single char)\n"
            "Examples: _archive, backup*, *.tmp, .hidden"
        )
        self.hint_label.setStyleSheet(self._hint_style())

        self.pattern_list = QListWidget()
        self.pattern_list.setStyleSheet(dialog_list_style())
        self.pattern_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self._populate_pattern_list()

        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("Enter pattern (e.g. _archive, backup*)")
        self.pattern_input.setStyleSheet(input_style())

        self.add_btn = QPushButton()
        self.add_btn.setIcon(QIcon(str(constants.ICONS_DIR / "plus.png")))
        self.add_btn.setIconSize(QSize(12, 12))
        self.add_btn.setStyleSheet(self._btn_style())

        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.setStyleSheet(self._btn_style(hover_color=constants.FAIL))

        # ── Departments tab ──────────────────────────────────────────────
        self.dept_section_label = QLabel("Departments")
        self.dept_section_label.setStyleSheet(self._section_style())

        self.dept_hint_label = QLabel(
            "These departments appear in the filter bar.\n"
            "\"All\" is always available and cannot be removed."
        )
        self.dept_hint_label.setStyleSheet(self._hint_style())

        self.dept_list = QListWidget()
        self.dept_list.setStyleSheet(dialog_list_style())
        self.dept_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._populate_dept_list()

        self.dept_input = QLineEdit()
        self.dept_input.setPlaceholderText("Enter department name")
        self.dept_input.setStyleSheet(input_style())

        self.dept_add_btn = QPushButton()
        self.dept_add_btn.setIcon(QIcon(str(constants.ICONS_DIR / "plus.png")))
        self.dept_add_btn.setIconSize(QSize(12, 12))
        self.dept_add_btn.setStyleSheet(self._btn_style())

        self.dept_remove_btn = QPushButton("Remove Selected")
        self.dept_remove_btn.setStyleSheet(self._btn_style(hover_color=constants.FAIL))

        self.dept_up_btn = QPushButton()
        self.dept_up_btn.setIcon(QIcon(str(constants.ICONS_DIR / "caret-arrow-up.png")))
        self.dept_up_btn.setIconSize(QSize(14, 14))
        self.dept_up_btn.setFixedWidth(36)
        self.dept_up_btn.setToolTip("Move up")
        self.dept_up_btn.setStyleSheet(self._btn_style())

        self.dept_down_btn = QPushButton()
        self.dept_down_btn.setIcon(QIcon(str(constants.ICONS_DIR / "down.png")))
        self.dept_down_btn.setIconSize(QSize(14, 14))
        self.dept_down_btn.setFixedWidth(36)
        self.dept_down_btn.setToolTip("Move down")
        self.dept_down_btn.setStyleSheet(self._btn_style())

        # ── Reviews tab ──────────────────────────────────────────────────
        self.review_section_label = QLabel("Review Session Types")
        self.review_section_label.setStyleSheet(self._section_style())

        self.review_hint_label = QLabel(
            "These types appear when creating a new review session.\n"
            "Admin-only — changes require the admin PIN to take effect at runtime."
        )
        self.review_hint_label.setStyleSheet(self._hint_style())

        self.review_list = QListWidget()
        self.review_list.setStyleSheet(dialog_list_style())
        self.review_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._populate_review_list()

        self.review_input = QLineEdit()
        self.review_input.setPlaceholderText("Enter session type (e.g. Director Dailies)")
        self.review_input.setStyleSheet(input_style())

        self.review_add_btn = QPushButton()
        self.review_add_btn.setIcon(QIcon(str(constants.ICONS_DIR / "plus.png")))
        self.review_add_btn.setIconSize(QSize(12, 12))
        self.review_add_btn.setStyleSheet(self._btn_style())

        self.review_remove_btn = QPushButton("Remove Selected")
        self.review_remove_btn.setStyleSheet(self._btn_style(hover_color=constants.FAIL))

        self.review_up_btn = QPushButton()
        self.review_up_btn.setIcon(QIcon(str(constants.ICONS_DIR / "caret-arrow-up.png")))
        self.review_up_btn.setIconSize(QSize(14, 14))
        self.review_up_btn.setFixedWidth(36)
        self.review_up_btn.setToolTip("Move up")
        self.review_up_btn.setStyleSheet(self._btn_style())

        self.review_down_btn = QPushButton()
        self.review_down_btn.setIcon(QIcon(str(constants.ICONS_DIR / "down.png")))
        self.review_down_btn.setIconSize(QSize(14, 14))
        self.review_down_btn.setFixedWidth(36)
        self.review_down_btn.setToolTip("Move down")
        self.review_down_btn.setStyleSheet(self._btn_style())

        # ── Pipeline tab ─────────────────────────────────────────────────
        self.pipeline_section_label = QLabel("Artist Registry")
        self.pipeline_section_label.setStyleSheet(self._section_style())

        self.pipeline_hint_label = QLabel(
            "Points BlastVault at your studio's artist registry for automatic\n"
            "identity and permission assignment.\n\n"
            "Source priority:\n"
            "  1.  BLASTVAULT_REGISTRY  environment variable  (set by IT)\n"
            "  2.  The path below\n"
            "  3.  Local  artists.json  in the app data folder  (default)"
        )
        self.pipeline_hint_label.setStyleSheet(self._hint_style())

        self.registry_path_label = QLabel("Registry Path / URL:")
        self.registry_path_label.setStyleSheet(
            f"color: {constants.TEXT_SEC}; background: transparent; font-size: 11px;"
        )

        self.registry_path_edit = QLineEdit()
        self.registry_path_edit.setText(constants.REGISTRY_PATH)
        self.registry_path_edit.setPlaceholderText(
            r"e.g.  \\server\pipeline\artists.json  or  http://pipeline/api/artists"
        )
        self.registry_path_edit.setStyleSheet(self._input_style())

        self.registry_browse_btn = QPushButton()
        self.registry_browse_btn.setIcon(QIcon(str(constants.ICONS_DIR / "folder.png")))
        self.registry_browse_btn.setIconSize(QSize(12, 12))
        self.registry_browse_btn.setToolTip("Browse for artists.json file")
        self.registry_browse_btn.setStyleSheet(self._btn_style())

        # Active source indicator — read-only, reflects current resolved source
        from core.artist_registry import source_label
        self.registry_source_lbl = QLabel(source_label())
        self.registry_source_lbl.setStyleSheet(
            f"background-color: {constants.BORDER}; color: {constants.TEXT_SEC};"
            f"border: 1px solid {constants.SPLITTER_COLOR}; border-radius: 4px;"
            f"padding: 6px 8px; font-size: 11px;"
        )
        self.registry_source_lbl.setWordWrap(True)

        # Registry status — shows who was found (or not) on last startup
        perm = constants.REGISTRY_PERMISSION
        if perm:
            _name = constants.CURRENT_USER
            _dept = constants.CURRENT_DEPARTMENT or "—"
            _icon = "✓" if perm == "admin" else "●"
            _status_txt = (
                f"{_icon}  Logged in as  {_name}  ({_dept})  ·  "
                f"Permission: {perm.capitalize()}"
            )
            _status_color = constants.SUCCESS if perm == "admin" else constants.ACCENT_HI
        else:
            _status_txt   = "⚠  Current user not found in registry — using local Settings."
            _status_color = constants.TEXT_SEC

        self.registry_user_lbl = QLabel(_status_txt)
        self.registry_user_lbl.setStyleSheet(
            f"color: {_status_color}; background: transparent; font-size: 11px;"
        )
        self.registry_user_lbl.setWordWrap(True)

        # Disable review tab controls if not admin
        _locked = constants.STATUS_LOCKED
        for w in (self.review_input, self.review_add_btn,
                  self.review_remove_btn, self.review_up_btn, self.review_down_btn):
            w.setEnabled(not _locked)

        self.review_locked_lbl = QLabel("🔒  Unlock admin mode to edit session types.")
        self.review_locked_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 11px; background: transparent;"
        )
        self.review_locked_lbl.setVisible(_locked)

        # ── Tools tab ────────────────────────────────────────────────────
        self.ffmpeg_section_label = QLabel("FFmpeg")
        self.ffmpeg_section_label.setStyleSheet(self._section_style())

        self.ffmpeg_hint_label = QLabel(
            "Required for video thumbnail extraction.\n"
            "FFmpeg is located automatically via PATH and common install locations.\n"
            "To change the version, update your system PATH."
        )
        self.ffmpeg_hint_label.setStyleSheet(self._hint_style())

        # Show the currently detected path (read-only)
        detected = constants.FFMPEG_PATH or "Not found"
        prefix   = "Detected:" if constants.FFMPEG_PATH else "⚠  Not found —"
        suffix   = "" if constants.FFMPEG_PATH else " install ffmpeg and add it to PATH"
        self.ffmpeg_detected_lbl = QLabel(f"{prefix}  {detected}{suffix}")
        self.ffmpeg_detected_lbl.setStyleSheet(
            f"background: transparent; font-size: 11px; "
            f"color: {constants.TEXT_SEC if constants.FFMPEG_PATH else constants.FAIL};"
        )
        self.ffmpeg_detected_lbl.setWordWrap(True)

        self.ffmpeg_test_btn = QPushButton("Test")
        self.ffmpeg_test_btn.setFixedWidth(54)
        self.ffmpeg_test_btn.setToolTip("Run ffmpeg -version to verify")
        self.ffmpeg_test_btn.setStyleSheet(self._btn_style())
        self.ffmpeg_test_btn.setEnabled(bool(constants.FFMPEG_PATH))

        self.ffmpeg_status_lbl = QLabel("")
        self.ffmpeg_status_lbl.setStyleSheet(
            f"background: transparent; font-size: 11px; color: {constants.TEXT_SEC};"
        )

        self.player_section_label = QLabel("BlastPlayer")
        self.player_section_label.setStyleSheet(self._section_style())

        self.player_hint_label = QLabel(
            "Path to BlastPlayer's main.py — used for \"Open in BlastPlayer\"."
        )
        self.player_hint_label.setStyleSheet(self._hint_style())

        self.player_path_edit = QLineEdit()
        self.player_path_edit.setText(str(constants.BLAST_PLAYER_PATH))
        self.player_path_edit.setStyleSheet(self._input_style())

        self.player_browse_btn = QPushButton()
        self.player_browse_btn.setIcon(QIcon(str(constants.ICONS_DIR / "folder.png")))
        self.player_browse_btn.setIconSize(QSize(12, 12))
        self.player_browse_btn.setToolTip("Browse for BlastPlayer main.py")
        self.player_browse_btn.setStyleSheet(self._btn_style())

        # ── Shared action buttons ────────────────────────────────────────
        self.import_btn = QPushButton("Import Config…")
        self.import_btn.setStyleSheet(self._btn_style())

        self.export_btn = QPushButton("Export Config…")
        self.export_btn.setStyleSheet(self._btn_style())
        # save_btn and cancel_btn created unconditionally at the top of this method

    # ------------------------------------------------------------------ #
    #  Layout construction                                                 #
    # ------------------------------------------------------------------ #

    def create_layout(self):
        # ── Non-admin: show only "Your Name" ─────────────────────────────
        if not constants.can_admin():
            main = QVBoxLayout(self)
            main.setContentsMargins(20, 20, 20, 20)
            main.setSpacing(10)
            user_row = QHBoxLayout()
            user_row.addWidget(self.user_name_label)
            user_row.addWidget(self.user_name_lineEdit)
            main.addLayout(user_row)
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            btn_row.addWidget(self.cancel_btn)
            btn_row.addWidget(self.save_btn)
            main.addLayout(btn_row)
            return

        # ── General tab ─────────────────────────────────────────────────
        general_tab = QWidget()
        gen = QVBoxLayout(general_tab)
        gen.setContentsMargins(15, 15, 15, 15)
        gen.setSpacing(10)

        user_row = QHBoxLayout()
        user_row.addWidget(self.user_name_label)
        user_row.addWidget(self.user_name_lineEdit)
        gen.addLayout(user_row)

        name_row = QHBoxLayout()
        name_row.addWidget(self.studio_name_label)
        name_row.addWidget(self.studio_name_lineEdit)
        gen.addLayout(name_row)

        root_row = QHBoxLayout()
        root_row.addWidget(self.studio_root_label)
        root_row.addWidget(self.studio_root_lineEdit)
        root_row.addWidget(self.studio_root_browse_btn)
        gen.addLayout(root_row)

        gen.addWidget(self.section_label)
        gen.addWidget(self.hint_label)
        gen.addWidget(self.pattern_list)

        pattern_row = QHBoxLayout()
        pattern_row.addWidget(self.pattern_input)
        pattern_row.addWidget(self.add_btn)
        gen.addLayout(pattern_row)

        gen.addWidget(self.remove_btn)

        gen.addStretch()

        # ── Departments tab ──────────────────────────────────────────────
        dept_tab = QWidget()
        dept = QVBoxLayout(dept_tab)
        dept.setContentsMargins(15, 15, 15, 15)
        dept.setSpacing(10)

        dept.addWidget(self.dept_section_label)
        dept.addWidget(self.dept_hint_label)

        list_row = QHBoxLayout()
        list_row.addWidget(self.dept_list)

        arrow_col = QVBoxLayout()
        arrow_col.setSpacing(4)
        arrow_col.addWidget(self.dept_up_btn)
        arrow_col.addWidget(self.dept_down_btn)
        arrow_col.addStretch()
        list_row.addLayout(arrow_col)
        dept.addLayout(list_row)

        add_row = QHBoxLayout()
        add_row.addWidget(self.dept_input)
        add_row.addWidget(self.dept_add_btn)
        dept.addLayout(add_row)

        dept.addWidget(self.dept_remove_btn)
        dept.addStretch()

        # ── Tools tab ────────────────────────────────────────────────────
        tools_tab = QWidget()
        tools = QVBoxLayout(tools_tab)
        tools.setContentsMargins(15, 15, 15, 15)
        tools.setSpacing(10)

        tools.addWidget(self.ffmpeg_section_label)
        tools.addWidget(self.ffmpeg_hint_label)
        tools.addWidget(self.ffmpeg_detected_lbl)

        ffmpeg_test_row = QHBoxLayout()
        ffmpeg_test_row.addWidget(self.ffmpeg_test_btn)
        ffmpeg_test_row.addStretch()
        tools.addLayout(ffmpeg_test_row)
        tools.addWidget(self.ffmpeg_status_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {constants.SPLITTER_COLOR};")
        sep.setFixedHeight(1)
        tools.addWidget(sep)

        tools.addWidget(self.player_section_label)
        tools.addWidget(self.player_hint_label)

        player_row = QHBoxLayout()
        player_row.addWidget(self.player_path_edit)
        player_row.addWidget(self.player_browse_btn)
        tools.addLayout(player_row)

        tools.addStretch()

        # ── Reviews tab ──────────────────────────────────────────────────
        reviews_tab = QWidget()
        reviews = QVBoxLayout(reviews_tab)
        reviews.setContentsMargins(15, 15, 15, 15)
        reviews.setSpacing(10)

        reviews.addWidget(self.review_section_label)
        reviews.addWidget(self.review_hint_label)
        reviews.addWidget(self.review_locked_lbl)

        rev_list_row = QHBoxLayout()
        rev_list_row.addWidget(self.review_list)

        rev_arrow_col = QVBoxLayout()
        rev_arrow_col.setSpacing(4)
        rev_arrow_col.addWidget(self.review_up_btn)
        rev_arrow_col.addWidget(self.review_down_btn)
        rev_arrow_col.addStretch()
        rev_list_row.addLayout(rev_arrow_col)
        reviews.addLayout(rev_list_row)

        rev_add_row = QHBoxLayout()
        rev_add_row.addWidget(self.review_input)
        rev_add_row.addWidget(self.review_add_btn)
        reviews.addLayout(rev_add_row)

        reviews.addWidget(self.review_remove_btn)
        reviews.addStretch()

        # ── Tab widget ───────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {constants.SPLITTER_COLOR};
                background: {constants.BG};
            }}
            QTabBar::tab {{
                background: {constants.BORDER};
                color: {constants.TEXT_SEC};
                padding: 8px 20px;
                border: none;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                background: {constants.BG};
                color: {constants.TEXT_PRI};
                border-bottom: 2px solid {constants.ACCENT_HI};
            }}
            QTabBar::tab:hover:!selected {{
                background: {constants.ACCENT};
                color: {constants.TEXT_PRI};
            }}
        """)
        # ── Pipeline tab ──────────────────────────────────────────────────
        pipeline_tab = QWidget()
        pipe = QVBoxLayout(pipeline_tab)
        pipe.setContentsMargins(15, 15, 15, 15)
        pipe.setSpacing(10)

        pipe.addWidget(self.pipeline_section_label)
        pipe.addWidget(self.pipeline_hint_label)

        pipe.addWidget(self.registry_path_label)
        reg_row = QHBoxLayout()
        reg_row.addWidget(self.registry_path_edit)
        reg_row.addWidget(self.registry_browse_btn)
        pipe.addLayout(reg_row)

        pipe.addWidget(self.registry_source_lbl)
        pipe.addWidget(self.registry_user_lbl)
        pipe.addStretch()

        self.tabs.addTab(general_tab,  "General")
        self.tabs.addTab(dept_tab,     "Departments")
        self.tabs.addTab(reviews_tab,  "Reviews")
        self.tabs.addTab(tools_tab,    "Tools")
        self.tabs.addTab(pipeline_tab, "Pipeline")

        # ── Main dialog layout ───────────────────────────────────────────
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(10)
        main.addWidget(self.tabs)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.import_btn)
        btn_row.addWidget(self.export_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        main.addLayout(btn_row)

    # ------------------------------------------------------------------ #
    #  Connections                                                         #
    # ------------------------------------------------------------------ #

    def create_connections(self):
        # Dialog buttons — always needed regardless of permission level
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn.clicked.connect(self.reject)

        # Non-admin: only name + close matter
        if not constants.can_admin():
            return

        # General
        self.studio_root_browse_btn.clicked.connect(self._on_browse_root)
        self.add_btn.clicked.connect(self._on_pattern_add)
        self.remove_btn.clicked.connect(self._on_pattern_remove)
        self.pattern_input.returnPressed.connect(self._on_pattern_add)

        # Departments
        self.dept_add_btn.clicked.connect(self._on_dept_add)
        self.dept_remove_btn.clicked.connect(self._on_dept_remove)
        self.dept_up_btn.clicked.connect(self._on_dept_move_up)
        self.dept_down_btn.clicked.connect(self._on_dept_move_down)
        self.dept_input.returnPressed.connect(self._on_dept_add)

        # Reviews
        self.review_add_btn.clicked.connect(self._on_review_type_add)
        self.review_remove_btn.clicked.connect(self._on_review_type_remove)
        self.review_up_btn.clicked.connect(self._on_review_type_move_up)
        self.review_down_btn.clicked.connect(self._on_review_type_move_down)
        self.review_input.returnPressed.connect(self._on_review_type_add)

        # Tools
        self.ffmpeg_test_btn.clicked.connect(self._on_test_ffmpeg)
        self.player_browse_btn.clicked.connect(self._on_browse_player)

        # Pipeline
        self.registry_browse_btn.clicked.connect(self._on_browse_registry)

        # Import / Export
        self.import_btn.clicked.connect(self._on_import_config)
        self.export_btn.clicked.connect(self._on_export_config)

    # ------------------------------------------------------------------ #
    #  General tab slots                                                   #
    # ------------------------------------------------------------------ #

    def _on_browse_root(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select Studio Root", self.studio_root_lineEdit.text()
        )
        if path:
            self.studio_root_lineEdit.setText(path)

    def _on_pattern_add(self):
        text = self.pattern_input.text().strip()
        if not text:
            return
        existing = [
            self.pattern_list.item(i).text()
            for i in range(self.pattern_list.count())
        ]
        if text not in existing:
            self.pattern_list.addItem(QListWidgetItem(text))
        self.pattern_input.clear()

    def _on_pattern_remove(self):
        for item in self.pattern_list.selectedItems():
            self.pattern_list.takeItem(self.pattern_list.row(item))

    # ------------------------------------------------------------------ #
    #  Departments tab slots                                               #
    # ------------------------------------------------------------------ #

    def _on_dept_add(self):
        text = self.dept_input.text().strip()
        if not text or text.lower() == "all":
            return
        existing = [
            self.dept_list.item(i).text()
            for i in range(self.dept_list.count())
        ]
        if text not in existing:
            self.dept_list.addItem(QListWidgetItem(text))
        self.dept_input.clear()

    def _on_dept_remove(self):
        for item in self.dept_list.selectedItems():
            self.dept_list.takeItem(self.dept_list.row(item))

    def _on_dept_move_up(self):
        row = self.dept_list.currentRow()
        if row <= 0:
            return
        item = self.dept_list.takeItem(row)
        self.dept_list.insertItem(row - 1, item)
        self.dept_list.setCurrentRow(row - 1)

    def _on_dept_move_down(self):
        row = self.dept_list.currentRow()
        if row < 0 or row >= self.dept_list.count() - 1:
            return
        item = self.dept_list.takeItem(row)
        self.dept_list.insertItem(row + 1, item)
        self.dept_list.setCurrentRow(row + 1)

    # ------------------------------------------------------------------ #
    #  Reviews tab slots                                                   #
    # ------------------------------------------------------------------ #

    def _on_review_type_add(self):
        text = self.review_input.text().strip()
        if not text:
            return
        existing = [
            self.review_list.item(i).text()
            for i in range(self.review_list.count())
        ]
        if text not in existing:
            self.review_list.addItem(QListWidgetItem(text))
        self.review_input.clear()

    def _on_review_type_remove(self):
        for item in self.review_list.selectedItems():
            self.review_list.takeItem(self.review_list.row(item))

    def _on_review_type_move_up(self):
        row = self.review_list.currentRow()
        if row <= 0:
            return
        item = self.review_list.takeItem(row)
        self.review_list.insertItem(row - 1, item)
        self.review_list.setCurrentRow(row - 1)

    def _on_review_type_move_down(self):
        row = self.review_list.currentRow()
        if row < 0 or row >= self.review_list.count() - 1:
            return
        item = self.review_list.takeItem(row)
        self.review_list.insertItem(row + 1, item)
        self.review_list.setCurrentRow(row + 1)

    # ------------------------------------------------------------------ #
    #  Tools tab slots                                                     #
    # ------------------------------------------------------------------ #

    def _on_test_ffmpeg(self):
        path = constants.FFMPEG_PATH
        if not path or not Path(path).is_file():
            self._set_ffmpeg_status("FFmpeg not found — install it and add to PATH.", ok=False)
            return
        try:
            result = subprocess.run(
                [path, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=5,
            )
            if result.returncode == 0:
                first_line = result.stdout.decode(errors="replace").splitlines()[0]
                self._set_ffmpeg_status(f"✓  {first_line}", ok=True)
            else:
                self._set_ffmpeg_status("Process returned an error.", ok=False)
        except FileNotFoundError:
            self._set_ffmpeg_status("Executable not found.", ok=False)
        except subprocess.TimeoutExpired:
            self._set_ffmpeg_status("Timed out.", ok=False)
        except Exception as e:
            self._set_ffmpeg_status(str(e), ok=False)

    def _set_ffmpeg_status(self, msg: str, ok: bool):
        color = constants.SUCCESS if ok else constants.FAIL
        self.ffmpeg_status_lbl.setStyleSheet(
            f"background: transparent; font-size: 11px; color: {color};"
        )
        self.ffmpeg_status_lbl.setText(msg)

    def _on_browse_player(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select BlastPlayer main.py",
            str(constants.BLAST_PLAYER_PATH.parent),
            "Python files (*.py);;All files (*)",
        )
        if path:
            self.player_path_edit.setText(path)

    def _on_browse_registry(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Artist Registry",
            str(Path.home()),
            "JSON files (*.json);;All files (*)",
        )
        if path:
            self.registry_path_edit.setText(path)

    # ------------------------------------------------------------------ #
    #  Import / Export slots                                               #
    # ------------------------------------------------------------------ #

    def _on_export_config(self):
        dest, _ = QFileDialog.getSaveFileName(
            self, "Export Config",
            str(Path.home() / "blastvault_config.json"),
            "JSON files (*.json);;All files (*)",
        )
        if not dest:
            return
        if export_config(dest):
            self.export_btn.setText("Exported ✓")
            QTimer.singleShot(2000, lambda: self.export_btn.setText("Export Config…"))
        else:
            self.export_btn.setText("Export Failed ✗")
            self.export_btn.setStyleSheet(self._btn_style(hover_color=constants.FAIL))
            def _reset_export():
                self.export_btn.setText("Export Config…")
                self.export_btn.setStyleSheet(self._btn_style())
            QTimer.singleShot(3000, _reset_export)

    def _on_import_config(self):
        src, _ = QFileDialog.getOpenFileName(
            self, "Import Config",
            str(Path.home()),
            "JSON files (*.json);;All files (*)",
        )
        if not src:
            return
        if import_config(src):
            # Refresh all list widgets to reflect the imported values
            self._populate_pattern_list()
            self._populate_dept_list()
            self._populate_review_list()
            self.user_name_lineEdit.setText(constants.CURRENT_USER)
            self.studio_name_lineEdit.setText(constants.STUDIO_NAME)
            self.studio_root_lineEdit.setText(constants.ROOT_DIR)
            self.player_path_edit.setText(str(constants.BLAST_PLAYER_PATH))
            self.registry_path_edit.setText(constants.REGISTRY_PATH)
            self.ffmpeg_status_lbl.setText("")
            self.settings_changed.emit()
        else:
            self.import_btn.setText("Import Failed ✗")
            self.import_btn.setStyleSheet(self._btn_style(hover_color=constants.FAIL))
            def _reset_import():
                self.import_btn.setText("Import Config…")
                self.import_btn.setStyleSheet(self._btn_style())
            QTimer.singleShot(3000, _reset_import)

    # ------------------------------------------------------------------ #
    #  Save                                                                #
    # ------------------------------------------------------------------ #

    def _on_save(self):
        # "Your Name" is editable by everyone
        user = self.user_name_lineEdit.text().strip()
        if user:
            constants.CURRENT_USER = user

        # Non-admin: only name matters — save and return
        if not constants.can_admin():
            save_config()
            self.settings_changed.emit()
            self.accept()
            return

        # Admin: save all settings
        constants.EXCLUDED_PATTERNS = [
            self.pattern_list.item(i).text()
            for i in range(self.pattern_list.count())
        ]
        constants.STUDIO_NAME = (
            self.studio_name_lineEdit.text().strip() or constants.STUDIO_NAME
        )
        constants.ROOT_DIR = (
            self.studio_root_lineEdit.text().strip() or constants.ROOT_DIR
        )

        # Departments — "All" always first, order preserved from list widget
        constants.DEPARTMENTS = ["All"] + [
            self.dept_list.item(i).text()
            for i in range(self.dept_list.count())
        ]

        # Review types (admin only — list may be disabled but values are preserved)
        if not constants.STATUS_LOCKED:
            constants.REVIEW_TYPES = [
                self.review_list.item(i).text()
                for i in range(self.review_list.count())
            ]

        # Tools
        player = self.player_path_edit.text().strip()
        if player:
            constants.BLAST_PLAYER_PATH = Path(player)

        # Pipeline
        constants.REGISTRY_PATH = self.registry_path_edit.text().strip()

        save_config()
        self.settings_changed.emit()
        self.accept()

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _populate_review_list(self):
        self.review_list.clear()
        for rt in constants.REVIEW_TYPES:
            self.review_list.addItem(QListWidgetItem(rt))

    def _populate_pattern_list(self):
        self.pattern_list.clear()
        for pattern in constants.EXCLUDED_PATTERNS:
            self.pattern_list.addItem(QListWidgetItem(pattern))

    def _populate_dept_list(self):
        """Populate departments list in their saved order, excluding 'All'."""
        self.dept_list.clear()
        for dept in constants.DEPARTMENTS:
            if dept != "All":
                self.dept_list.addItem(QListWidgetItem(dept))

    def _section_style(self) -> str:
        return (
            f"font-size: 14px; font-weight: bold;"
            f" color: {constants.TEXT_PRI}; background: transparent;"
        )

    def _hint_style(self) -> str:
        return f"font-size: 11px; color: {constants.TEXT_SEC}; background: transparent;"

    def _input_style(self) -> str:
        return f"""
            QLineEdit {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.BG};
                border-radius: 4px;
                padding: 4px 5px;
            }}
            QLineEdit:focus {{ border: 1px solid {constants.ACCENT}; }}
        """

    def _btn_style(self, hover_color: str = None) -> str:
        hover = hover_color or constants.ACCENT
        return f"""
            QPushButton {{
                background-color: {constants.SPLITTER_COLOR};
                color: {constants.TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
        """


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from core.styles import styleSheet, qt_argv
    app = QApplication(qt_argv())
    app.setStyle("Fusion")
    app.setStyleSheet(styleSheet)
    dlg = SettingsDialog()
    dlg.exec_()
    sys.exit(0)
