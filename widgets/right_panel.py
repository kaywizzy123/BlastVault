import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from PyQt5.QtWidgets import QFormLayout, QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QSizePolicy
from PyQt5.QtCore import Qt
import datetime
from core import constants, styles
from utils.collapsible_btn import CollapsibleWidget



class RightPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.setContentsMargins(0, 0, 0, 0)

    def create_widgets(self):
        self.file_label = QLabel("File Name:")
        self.file_details = QLineEdit()
        self.file_details.setReadOnly(True)
        self.file_details.setFocusPolicy(Qt.NoFocus)
        self.file_details.setStyleSheet(styles.input_style())
        self.file_details.setFixedHeight(25)
        

        self.department_label = QLabel("Department:")
        self.department_details = QLineEdit()
        self.department_details.setReadOnly(True)
        self.department_details.setFocusPolicy(Qt.NoFocus)
        self.department_details.setStyleSheet(styles.input_style())
        self.department_details.setFixedHeight(25)
        
        self.artist_label = QLabel("Artist:")
        self.artist_details = QLineEdit()
        self.artist_details.setReadOnly(True)
        self.artist_details.setFocusPolicy(Qt.NoFocus)
        self.artist_details.setStyleSheet(styles.input_style())
        self.artist_details.setFixedHeight(25)

        self.version_label = QLabel("Version:")
        self.version_details = QLineEdit()
        self.version_details.setReadOnly(True)
        self.version_details.setFocusPolicy(Qt.NoFocus)
        self.version_details.setStyleSheet(styles.input_style())
        self.version_details.setFixedHeight(25)

        self.date_label = QLabel("Created:")
        self.date_details = QLineEdit()
        self.date_details.setReadOnly(True)
        self.date_details.setFocusPolicy(Qt.NoFocus)
        self.date_details.setStyleSheet(styles.input_style())
        self.date_details.setFixedHeight(25)

        self.description_label = QLabel("Description:")
        self.description_details = QTextEdit()
        self.description_details.setReadOnly(True)
        self.description_details.setFocusPolicy(Qt.NoFocus)
        self.description_details.setFixedHeight(100)
        self.description_details.setStyleSheet(styles.input_style())
        
        self.file_path_label = QLabel("File Path:")
        self.file_path_details = QLineEdit()
        self.file_path_details.setReadOnly(True)
        self.file_path_details.setFocusPolicy(Qt.NoFocus)
        self.file_path_details.setStyleSheet(styles.input_style())
        self.file_path_details.setFixedHeight(25)
        
        self.resolution_label = QLabel("Resolution:")
        self.resolution_details = QLineEdit()
        self.resolution_details.setReadOnly(True)
        self.resolution_details.setFocusPolicy(Qt.NoFocus)
        self.resolution_details.setStyleSheet(styles.input_style())
        self.resolution_details.setFixedHeight(25)

        self.media_details_widget = CollapsibleWidget("Media Details")
        media_form = QFormLayout()
        media_form.setContentsMargins(10, 4, 10, 4)
        media_form.setSpacing(4)
        media_form.addRow(self.resolution_label, self.resolution_details)
        self.media_details_widget.add_layout(media_form)

    def create_layout(self):
        info_layout = QFormLayout()
        info_layout.setContentsMargins(10, 10, 10, 10)
        info_layout.setSpacing(4)
        info_layout.addRow(self.file_label, self.file_details)
        info_layout.addRow(self.department_label, self.department_details)
        info_layout.addRow(self.artist_label, self.artist_details)
        info_layout.addRow(self.version_label, self.version_details)
        info_layout.addRow(self.date_label, self.date_details)
        info_layout.addRow(self.description_label, self.description_details)
        info_layout.addRow(self.file_path_label, self.file_path_details)

        info_container = QWidget()
        info_container.setLayout(info_layout)
        info_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(info_container)
        self.main_layout.addWidget(self.media_details_widget)
        self.main_layout.addStretch()

    def create_connections(self):
        pass


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from core.styles import styleSheet
    app = QApplication(sys.argv + ["-platform", "windows:darkmode=1"])
    app.setStyle("Fusion")
    app.setStyleSheet(styleSheet)
    w = RightPanel()
    w.resize(300, 600)
    w.show()
    sys.exit(app.exec_())
