import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import (
    QDialog, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QHBoxLayout
)
from PyQt5.QtCore import Qt

from core import constants
from core.config import is_excluded
from core.styles import dialog_list_style, input_style
from utils.icons import colored_icon


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
                background-color: {constants.SPLITTER_COLOR};
                color: {constants.TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {constants.ACCENT_HI};
            }}
        """)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.SPLITTER_COLOR};
                color: {constants.TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {constants.FAIL};
            }}
        """)

    def populate_list(self, filter_text=""):
        self.list_widget.clear()
        if not Path(constants.ROOT_DIR).exists():
            return
        try:
            for entry in sorted(Path(constants.ROOT_DIR).iterdir(), key=lambda p: p.name.lower()):
                if entry.is_dir() and not is_excluded(entry.name):
                    if filter_text.lower() in entry.name.lower():
                        item = QListWidgetItem(entry.name)
                        item.setData(Qt.UserRole, str(entry))
                        item.setCheckState(Qt.Unchecked)
                        item.setIcon(colored_icon(constants.ACCENT, closed=True))
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


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from core.styles import styleSheet, qt_argv
    app = QApplication(qt_argv())
    app.setStyle("Fusion")
    app.setStyleSheet(styleSheet)
    dlg = AddCatalogDialog()
    dlg.exec_()
    sys.exit(0)

