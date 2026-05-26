import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import (
    QDialog, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QHBoxLayout, QAbstractItemView
)
from PyQt5.QtCore import Qt

from core import constants
from core.styles import dialog_list_style, input_style


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
                background-color: {constants.BORDER};
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


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
    from core.styles import styleSheet
    from core.constants import ACCENT
    from utils.icons import colored_icon
    app = QApplication(sys.argv + ["-platform", "windows:darkmode=1"])
    app.setStyle("Fusion")
    app.setStyleSheet(styleSheet)
    tree = QTreeWidget()
    root = tree.invisibleRootItem()
    for name in ["Show_A", "Show_B", "Show_C"]:
        QTreeWidgetItem(root, [name])
    dlg = RemoveCatalogDialog(root, colored_icon(ACCENT, closed=True))
    dlg.exec_()
    sys.exit(0)
