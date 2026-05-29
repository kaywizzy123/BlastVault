import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QHBoxLayout, QAbstractItemView,
    QFileDialog, QTabWidget, QWidget,
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon

from core import constants
from core.config import save_config
from core.styles import dialog_list_style, input_style


class SettingsDialog(QDialog):
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(500, 580)
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
        self.studio_name_label   = QLabel("Studio Name:")
        self.studio_name_lineEdit = QLineEdit()
        self.studio_name_lineEdit.setText(constants.STUDIO_NAME)
        self.studio_name_lineEdit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.BG};
                border-radius: 4px;
                padding: 4px 5px;
            }}
            QLineEdit:focus {{ border: 1px solid {constants.ACCENT}; }}
        """)

        self.studio_root_label   = QLabel("Studio Root:")
        self.studio_root_lineEdit = QLineEdit()
        self.studio_root_lineEdit.setText(constants.ROOT_DIR)
        self.studio_root_lineEdit.setPlaceholderText(
            r"e.g.  Z:\SHOWS  or  \\server\shows  or  /Volumes/server/shows"
        )
        self.studio_root_lineEdit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.BG};
                border-radius: 4px;
                padding: 4px 5px;
            }}
            QLineEdit:focus {{ border: 1px solid {constants.ACCENT}; }}
        """)

        self.studio_root_browse_btn = QPushButton()
        self.studio_root_browse_btn.setIcon(QIcon(str(constants.ICONS_DIR / "folder.png")))
        self.studio_root_browse_btn.setIconSize(QSize(12, 12))
        self.studio_root_browse_btn.setStyleSheet(self._btn_style())

        self.section_label = QLabel("Excluded Folder Patterns")
        self.section_label.setStyleSheet(f"""
            font-size: 14px; font-weight: bold;
            color: {constants.TEXT_PRI}; background: transparent;
        """)

        self.hint_label = QLabel(
            "Folders matching these patterns will be hidden.\n"
            "Supports wildcards: * (any chars), ? (single char)\n"
            "Examples: _archive, backup*, *.tmp, .hidden"
        )
        self.hint_label.setStyleSheet(
            f"font-size: 11px; color: {constants.TEXT_SEC}; background: transparent;"
        )

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
        self.dept_section_label.setStyleSheet(f"""
            font-size: 14px; font-weight: bold;
            color: {constants.TEXT_PRI}; background: transparent;
        """)

        self.dept_hint_label = QLabel(
            "These departments appear in the filter bar.\n"
            "\"All\" is always available and cannot be removed."
        )
        self.dept_hint_label.setStyleSheet(
            f"font-size: 11px; color: {constants.TEXT_SEC}; background: transparent;"
        )

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

        # ── Artists tab ──────────────────────────────────────────────────
        self.artist_section_label = QLabel("Artists")
        self.artist_section_label.setStyleSheet(f"""
            font-size: 14px; font-weight: bold;
            color: {constants.TEXT_PRI}; background: transparent;
        """)

        self.artist_hint_label = QLabel(
            "These artists appear in the filter bar.\n"
            "Use the same username token that appears in your filenames.\n"
            "\"All\" is always available and cannot be removed."
        )
        self.artist_hint_label.setStyleSheet(
            f"font-size: 11px; color: {constants.TEXT_SEC}; background: transparent;"
        )

        self.artist_list = QListWidget()
        self.artist_list.setStyleSheet(dialog_list_style())
        self.artist_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._populate_artist_list()

        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("Enter artist username (e.g. oogunremi)")
        self.artist_input.setStyleSheet(input_style())

        self.artist_add_btn = QPushButton()
        self.artist_add_btn.setIcon(QIcon(str(constants.ICONS_DIR / "plus.png")))
        self.artist_add_btn.setIconSize(QSize(12, 12))
        self.artist_add_btn.setStyleSheet(self._btn_style())

        self.artist_remove_btn = QPushButton("Remove Selected")
        self.artist_remove_btn.setStyleSheet(self._btn_style(hover_color=constants.FAIL))

        self.artist_up_btn = QPushButton()
        self.artist_up_btn.setIcon(QIcon(str(constants.ICONS_DIR / "caret-arrow-up.png")))
        self.artist_up_btn.setIconSize(QSize(14, 14))
        self.artist_up_btn.setFixedWidth(36)
        self.artist_up_btn.setToolTip("Move up")
        self.artist_up_btn.setStyleSheet(self._btn_style())

        self.artist_down_btn = QPushButton()
        self.artist_down_btn.setIcon(QIcon(str(constants.ICONS_DIR / "down.png")))
        self.artist_down_btn.setIconSize(QSize(14, 14))
        self.artist_down_btn.setFixedWidth(36)
        self.artist_down_btn.setToolTip("Move down")
        self.artist_down_btn.setStyleSheet(self._btn_style())

        # ── Shared action buttons ────────────────────────────────────────
        self.save_btn = QPushButton("Save")
        self.save_btn.setFixedWidth(100)
        self.save_btn.setStyleSheet(self._btn_style(hover_color=constants.ACCENT_HI))

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.setStyleSheet(self._btn_style(hover_color=constants.FAIL))

    # ------------------------------------------------------------------ #
    #  Layout construction                                                 #
    # ------------------------------------------------------------------ #

    def create_layout(self):
        # ── General tab ─────────────────────────────────────────────────
        general_tab = QWidget()
        gen = QVBoxLayout(general_tab)
        gen.setContentsMargins(15, 15, 15, 15)
        gen.setSpacing(10)

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

        # ── Artists tab ──────────────────────────────────────────────────
        artist_tab = QWidget()
        art = QVBoxLayout(artist_tab)
        art.setContentsMargins(15, 15, 15, 15)
        art.setSpacing(10)

        art.addWidget(self.artist_section_label)
        art.addWidget(self.artist_hint_label)

        artist_list_row = QHBoxLayout()
        artist_list_row.addWidget(self.artist_list)

        artist_arrow_col = QVBoxLayout()
        artist_arrow_col.setSpacing(4)
        artist_arrow_col.addWidget(self.artist_up_btn)
        artist_arrow_col.addWidget(self.artist_down_btn)
        artist_arrow_col.addStretch()
        artist_list_row.addLayout(artist_arrow_col)
        art.addLayout(artist_list_row)

        artist_add_row = QHBoxLayout()
        artist_add_row.addWidget(self.artist_input)
        artist_add_row.addWidget(self.artist_add_btn)
        art.addLayout(artist_add_row)

        art.addWidget(self.artist_remove_btn)
        art.addStretch()

        # ── Tab widget ───────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px;
            }}
            QTabBar::tab {{
                background: {constants.SPLITTER_COLOR};
                color: {constants.TEXT_SEC};
                padding: 6px 18px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background: {constants.BORDER};
                color: {constants.TEXT_PRI};
            }}
            QTabBar::tab:hover:!selected {{
                background: {constants.ACCENT};
                color: {constants.TEXT_PRI};
            }}
        """)
        self.tabs.addTab(general_tab,  "General")
        self.tabs.addTab(dept_tab,     "Departments")
        self.tabs.addTab(artist_tab,   "Artists")

        # ── Main dialog layout ───────────────────────────────────────────
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(10)
        main.addWidget(self.tabs)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        main.addLayout(btn_row)

    # ------------------------------------------------------------------ #
    #  Connections                                                         #
    # ------------------------------------------------------------------ #

    def create_connections(self):
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

        # Artists
        self.artist_add_btn.clicked.connect(self._on_artist_add)
        self.artist_remove_btn.clicked.connect(self._on_artist_remove)
        self.artist_up_btn.clicked.connect(self._on_artist_move_up)
        self.artist_down_btn.clicked.connect(self._on_artist_move_down)
        self.artist_input.returnPressed.connect(self._on_artist_add)

        # Dialog buttons
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn.clicked.connect(self.reject)

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
        if not text:
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
    #  Artists tab slots                                                   #
    # ------------------------------------------------------------------ #

    def _on_artist_add(self):
        text = self.artist_input.text().strip().lower()
        if not text:
            return
        existing = [
            self.artist_list.item(i).text()
            for i in range(self.artist_list.count())
        ]
        if text not in existing:
            self.artist_list.addItem(QListWidgetItem(text))
        self.artist_input.clear()

    def _on_artist_remove(self):
        for item in self.artist_list.selectedItems():
            self.artist_list.takeItem(self.artist_list.row(item))

    def _on_artist_move_up(self):
        row = self.artist_list.currentRow()
        if row <= 0:
            return
        item = self.artist_list.takeItem(row)
        self.artist_list.insertItem(row - 1, item)
        self.artist_list.setCurrentRow(row - 1)

    def _on_artist_move_down(self):
        row = self.artist_list.currentRow()
        if row < 0 or row >= self.artist_list.count() - 1:
            return
        item = self.artist_list.takeItem(row)
        self.artist_list.insertItem(row + 1, item)
        self.artist_list.setCurrentRow(row + 1)

    # ------------------------------------------------------------------ #
    #  Save                                                                #
    # ------------------------------------------------------------------ #

    def _on_save(self):
        # General
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

        # Departments — "All" is always first, never stored in the list widget
        constants.DEPARTMENTS = ["All"] + [
            self.dept_list.item(i).text()
            for i in range(self.dept_list.count())
        ]

        # Artists — same pattern as departments
        constants.ARTISTS = ["All"] + [
            self.artist_list.item(i).text()
            for i in range(self.artist_list.count())
        ]

        save_config()
        self.settings_changed.emit()
        self.accept()

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _populate_pattern_list(self):
        self.pattern_list.clear()
        for pattern in constants.EXCLUDED_PATTERNS:
            self.pattern_list.addItem(QListWidgetItem(pattern))

    def _populate_dept_list(self):
        """Populate the departments list, excluding the always-present 'All'."""
        self.dept_list.clear()
        for dept in constants.DEPARTMENTS:
            if dept != "All":
                self.dept_list.addItem(QListWidgetItem(dept))

    def _populate_artist_list(self):
        """Populate the artists list, excluding the always-present 'All'."""
        self.artist_list.clear()
        for artist in constants.ARTISTS:
            if artist != "All":
                self.artist_list.addItem(QListWidgetItem(artist))

    def _btn_style(self, hover_color: str = None) -> str:
        hover = hover_color or constants.BORDER
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
