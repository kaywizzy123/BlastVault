import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QFileDialog,
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QPixmap

from core import constants
from core.config import save_config


class FirstRunDialog(QDialog):
    """Shown once on first launch to let the artist set their Studio Root."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to BlastVault")
        self.setFixedSize(520, 450)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    # ------------------------------------------------------------------ #
    #  Build UI                                                            #
    # ------------------------------------------------------------------ #

    def create_widgets(self):
        # Logo / icon
        self.logo_label = QLabel()
        icon_path = str(constants.ICONS_DIR / "bv.png")
        pix = QPixmap(icon_path)
        if not pix.isNull():
            self.logo_label.setPixmap(
                pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        self.logo_label.setAlignment(Qt.AlignCenter)

        # Heading
        self.heading_label = QLabel("Welcome to BlastVault")
        self.heading_label.setAlignment(Qt.AlignCenter)
        self.heading_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {constants.TEXT_PRI};
            background: transparent;
        """)

        # Sub-text
        self.sub_label = QLabel(
            "Before you get started, set up your profile and tell\n"
            "BlastVault where your files live. You can change all of\n"
            "this at any time in Options → Settings."
        )
        self.sub_label.setAlignment(Qt.AlignCenter)
        self.sub_label.setStyleSheet(f"""
            font-size: 12px;
            color: {constants.TEXT_SEC};
            background: transparent;
        """)

        # Your name field
        self.user_name_label = QLabel("Your Name:")
        self.user_name_label.setStyleSheet(f"color: {constants.TEXT_PRI}; background: transparent;")

        self.user_name_lineEdit = QLineEdit()
        self.user_name_lineEdit.setText(constants.CURRENT_USER)
        self.user_name_lineEdit.setPlaceholderText("e.g.  oogunremi")
        self.user_name_lineEdit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid {constants.ACCENT};
            }}
        """)

        # Studio name field
        self.name_label = QLabel("Studio Name:")
        self.name_label.setStyleSheet(f"color: {constants.TEXT_PRI}; background: transparent;")

        self.name_lineEdit = QLineEdit()
        self.name_lineEdit.setText(constants.STUDIO_NAME)
        self.name_lineEdit.setPlaceholderText("e.g.  Pixar Animation Studios")
        self.name_lineEdit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid {constants.ACCENT};
            }}
        """)

        # Root path field
        self.root_label = QLabel("Studio Root Folder:")
        self.root_label.setStyleSheet(f"color: {constants.TEXT_PRI}; background: transparent;")

        self.root_lineEdit = QLineEdit()
        self.root_lineEdit.setText(constants.ROOT_DIR)
        self.root_lineEdit.setPlaceholderText(
            r"e.g.  Z:\SHOWS  or  \\server\shows  or  /Volumes/server/shows"
        )
        self.root_lineEdit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid {constants.ACCENT};
            }}
        """)

        self.browse_btn = QPushButton()
        self.browse_btn.setIcon(QIcon(str(constants.ICONS_DIR / "folder.png")))
        self.browse_btn.setIconSize(QSize(14, 14))
        self.browse_btn.setToolTip("Browse for folder")
        self.browse_btn.setStyleSheet(f"""
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

        # Action buttons
        self.confirm_btn = QPushButton("Get Started")
        self.confirm_btn.setFixedWidth(130)
        self.confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT};
                color: {constants.TEXT_PRI};
                border: none;
                padding: 8px 12px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {constants.ACCENT_HI};
            }}
        """)

        self.skip_btn = QPushButton("Skip for now")
        self.skip_btn.setFixedWidth(110)
        self.skip_btn.setToolTip("You can set this later in Options → Settings")
        self.skip_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {constants.TEXT_SEC};
                border: none;
                padding: 8px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                color: {constants.TEXT_PRI};
            }}
        """)

    def create_layout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(12)

        layout.addWidget(self.logo_label)
        layout.addWidget(self.heading_label)
        layout.addWidget(self.sub_label)
        layout.addSpacing(8)

        layout.addWidget(self.user_name_label)
        layout.addWidget(self.user_name_lineEdit)

        layout.addSpacing(4)

        layout.addWidget(self.name_label)
        layout.addWidget(self.name_lineEdit)

        layout.addSpacing(4)

        layout.addWidget(self.root_label)

        path_row = QHBoxLayout()
        path_row.addWidget(self.root_lineEdit)
        path_row.addWidget(self.browse_btn)
        layout.addLayout(path_row)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.skip_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.confirm_btn)
        layout.addLayout(btn_row)

    def create_connections(self):
        self.browse_btn.clicked.connect(self._on_browse)
        self.confirm_btn.clicked.connect(self._on_confirm)
        self.skip_btn.clicked.connect(self.reject)

    # ------------------------------------------------------------------ #
    #  Slots                                                               #
    # ------------------------------------------------------------------ #

    def _on_browse(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select Studio Root Folder", self.root_lineEdit.text()
        )
        if path:
            self.root_lineEdit.setText(path)

    def _on_confirm(self):
        user = self.user_name_lineEdit.text().strip()
        if user:
            constants.CURRENT_USER = user
        name = self.name_lineEdit.text().strip()
        if name:
            constants.STUDIO_NAME = name
        path = self.root_lineEdit.text().strip()
        if path:
            constants.ROOT_DIR = path
        save_config()
        self.accept()


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from core.styles import styleSheet, qt_argv
    app = QApplication(qt_argv())
    app.setStyle("Fusion")
    app.setStyleSheet(styleSheet)
    dlg = FirstRunDialog()
    dlg.exec_()
    sys.exit(0)
