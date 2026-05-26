import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QFrame
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon

from core import constants
from core.constants import ICONS_DIR
from core.styles import header_btn_style


class HeaderWidget(QWidget):
    toggle_view = pyqtSignal()
    search_changed = pyqtSignal(str)
    department_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(40)
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.studio_label = QLabel(constants.STUDIO_NAME)
        self.studio_label.setStyleSheet(
            f"background:transparent; font-size: 16px; font-weight: bold; "
            f"color: {constants.ACCENT_HI}; letter-spacing: 2px;"
        )

        self.department_filter_label = QLabel("Department:")
        self.department_filter_label.setStyleSheet(
            f"background:transparent; color: {constants.TEXT_SEC};"
        )
        self.department_filter_combobox = QComboBox()
        self.department_filter_combobox.setFixedWidth(150)
        self.department_filter_combobox.addItems(constants.DEPARTMENTS)
        _arrow = str(ICONS_DIR / "arrow-down-sign-to-navigate.png").replace("\\", "/")
        _combo_style = f"""
            QComboBox {{
                background-color: {constants.BG};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QComboBox:focus {{
                border: 1px solid {constants.ACCENT};
            }}
            QComboBox QAbstractItemView {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.BG};
                outline: none;
                selection-background-color: {constants.ACCENT};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: url({_arrow});
                width: 12px;
                height: 12px;
            }}
        """
        self.department_filter_combobox.setStyleSheet(_combo_style)

        self.artist_filter_label = QLabel("Artist:")
        self.artist_filter_label.setStyleSheet(
            f"background:transparent; color: {constants.TEXT_SEC};"
        )
        self.artist_filter_combobox = QComboBox()
        self.artist_filter_combobox.setFixedWidth(150)
        self.artist_filter_combobox.setStyleSheet(_combo_style)

        for combo in (self.department_filter_combobox, self.artist_filter_combobox):
            combo.view().setFrameShape(QFrame.NoFrame)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.setFixedWidth(500)
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                background-color: {constants.BG};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QLineEdit:focus {{
                border: 1px solid {constants.ACCENT};
            }}
        """)

        self.toggle_view_btn = QPushButton()
        self.toggle_view_btn.setIcon(QIcon(str(ICONS_DIR / "dashboards.png")))
        self.toggle_view_btn.setFixedSize(28, 28)
        self.toggle_view_btn.setIconSize(QSize(20, 20))
        self.toggle_view_btn.setCheckable(True)
        self.toggle_view_btn.setChecked(True)
        self.toggle_view_btn.setStyleSheet(header_btn_style())

        self.refresh_btn = QPushButton()
        self.refresh_btn.setIcon(QIcon(str(ICONS_DIR / "refresh.png")))
        self.refresh_btn.setFixedSize(28, 28)
        self.refresh_btn.setIconSize(QSize(20, 20))
        self.refresh_btn.setStyleSheet(header_btn_style())

    def update_studio_label(self, name):
        self.studio_label.setText(name)

    def reload_departments(self):
        self.department_filter_combobox.clear()
        self.department_filter_combobox.addItems(constants.DEPARTMENTS)

    def create_layout(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 0, 10, 0)
        self.main_layout.setSpacing(6)
        self.main_layout.addWidget(self.studio_label)
        self.main_layout.addStretch()
        self.main_layout.addWidget(self.search_bar)
        self.main_layout.addStretch()
        self.main_layout.addWidget(self.department_filter_label)
        self.main_layout.addWidget(self.department_filter_combobox)
        self.main_layout.addWidget(self.artist_filter_label)
        self.main_layout.addWidget(self.artist_filter_combobox)
        self.main_layout.addWidget(self.toggle_view_btn)
        self.main_layout.addWidget(self.refresh_btn)

    def create_connections(self):
        self.toggle_view_btn.clicked.connect(self.on_toggle_view)
        self.refresh_btn.clicked.connect(self.on_refresh)
        self.search_bar.textChanged.connect(self.search_changed)
        self.department_filter_combobox.currentTextChanged.connect(self.department_changed)

    def on_toggle_view(self):
        if self.toggle_view_btn.isChecked():
            self.toggle_view_btn.setIcon(QIcon(str(ICONS_DIR / "dashboards.png")))
        else:
            self.toggle_view_btn.setIcon(QIcon(str(ICONS_DIR / "grid.png")))
        self.toggle_view.emit()

    def on_refresh(self):
        pass


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from core.styles import styleSheet
    app = QApplication(sys.argv + ["-platform", "windows:darkmode=1"])
    app.setStyle("Fusion")
    app.setStyleSheet(styleSheet)
    w = HeaderWidget()
    w.show()
    sys.exit(app.exec_())
