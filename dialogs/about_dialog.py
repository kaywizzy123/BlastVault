import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
)
from PyQt5.QtCore import Qt

from core import constants


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
            color: {constants.TEXT_PRI};
            background: transparent;
        """)
        self.title_label.setAlignment(Qt.AlignCenter)

        self.desc_label = QLabel("This app was designed and developed by\nOluwakayode Ogunremi\n©2026")
        self.desc_label.setStyleSheet(f"""
            font-size: 13px;
            color: {constants.TEXT_SEC};
            background: transparent;
        """)
        self.desc_label.setAlignment(Qt.AlignCenter)

        self.close_button = QPushButton("Close")
        self.close_button.setFixedWidth(100)
        self.close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.SPLITTER_COLOR};
                color: {constants.TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {constants.ACCENT};
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


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from core.styles import styleSheet, qt_argv
    app = QApplication(qt_argv())
    app.setStyle("Fusion")
    app.setStyleSheet(styleSheet)
    dlg = AboutDialog()
    dlg.exec_()
    sys.exit(0)

