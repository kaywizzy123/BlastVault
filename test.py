import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QPoint

class CustomWindow(QWidget):
    def __init__(self):
        super().__init__()
        # Hide default OS title bar
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(500, 400)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- CREATE CUSTOM TITLE BAR ---
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(35)
        # Make the bar black and text white
        self.title_bar.setStyleSheet("background-color: black; color: white;")
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)

        # Title/Icon Label
        self.title_label = QLabel("★ My Custom Black Bar")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        # Close Button
        self.close_button = QPushButton("✕")
        self.close_button.setFixedSize(30, 25)
        self.close_button.setStyleSheet("background: transparent; color: white; border: none;")
        self.close_button.clicked.connect(self.close)
        title_layout.addWidget(self.close_button)

        # Add title bar and content area to main window
        main_layout.addWidget(self.title_bar)
        
        # App Content Area
        self.content = QWidget()
        self.content.setStyleSheet("background-color: #222222;") # Dark gray content area
        main_layout.addWidget(self.content)

        # Variables to track window dragging
        self.drag_position = QPoint()

    # Enable window dragging since the native title bar is gone
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

app = QApplication(sys.argv)
window = CustomWindow()
window.show()
sys.exit(app.exec())
