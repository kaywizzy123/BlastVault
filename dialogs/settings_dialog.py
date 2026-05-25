import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QHBoxLayout, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal

from core import constants
from core.config import save_config
from core.styles import dialog_list_style, input_style


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
        self.studio_name_label = QLabel("Studio Name:")
        self.studio_name_lineEdit = QLineEdit()
        self.studio_name_lineEdit.setText(constants.STUDIO_NAME)
        self.studio_name_lineEdit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.BG};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QLineEdit:focus {{
                border: 1px solid {constants.ACCENT};
            }}
        """)

        self.section_label = QLabel("Excluded Folder Patterns")
        self.section_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {constants.TEXT_PRI};
            background: transparent;
        """)

        self.hint_label = QLabel(
            "Folders matching these patterns will be hidden.\n"
            "Supports wildcards: * (any chars), ? (single char)\n"
            "Examples: _archive, backup*, *.tmp, .hidden"
        )
        self.hint_label.setStyleSheet(f"""
            font-size: 11px;
            color: {constants.TEXT_SEC};
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
                background-color: {constants.ACCENT};
                color: {constants.TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {constants.ACCENT_HI};
            }}
        """)

        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.FAIL};
                color: {constants.TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {constants.ACCENT};
            }}
        """)

        self.save_btn = QPushButton("Save")
        self.save_btn.setFixedWidth(100)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT};
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
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {constants.ACCENT};
            }}
        """)

    def populate_list(self):
        self.pattern_list.clear()
        for pattern in constants.EXCLUDED_PATTERNS:
            self.pattern_list.addItem(QListWidgetItem(pattern))

    def create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        studio_name_layout = QHBoxLayout()
        studio_name_layout.addWidget(self.studio_name_label)
        studio_name_layout.addWidget(self.studio_name_lineEdit)
        main_layout.addLayout(studio_name_layout)

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
        if text not in constants.EXCLUDED_PATTERNS:
            self.pattern_list.addItem(QListWidgetItem(text))
        self.pattern_input.clear()

    def on_remove(self):
        for item in self.pattern_list.selectedItems():
            self.pattern_list.takeItem(self.pattern_list.row(item))

    def on_save(self):
        constants.EXCLUDED_PATTERNS = [
            self.pattern_list.item(i).text()
            for i in range(self.pattern_list.count())
        ]
        constants.STUDIO_NAME = self.studio_name_lineEdit.text().strip() or constants.STUDIO_NAME
        save_config()
        self.settings_changed.emit()
        self.accept()


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from core.styles import styleSheet
    app = QApplication(sys.argv + ["-platform", "windows:darkmode=1"])
    app.setStyle("Fusion")
    app.setStyleSheet(styleSheet)
    dlg = SettingsDialog()
    dlg.exec_()
    sys.exit(0)
