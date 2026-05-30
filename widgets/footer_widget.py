import sys
import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer

from core import constants


class FooterWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(25)
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        _style = f"background: transparent; color: {constants.TEXT_SEC}; font-size: 12px;"
        self.items_label = QLabel("Items: 0")
        self.items_label.setStyleSheet(_style)
        self.selected_label = QLabel("Selected: 0")
        self.selected_label.setStyleSheet(_style)

        # ── Auto-refresh indicator ───────────────────────────────────────
        self._refresh_label = QLabel()
        self._refresh_label.setStyleSheet(
            f"background: transparent; color: {constants.SUCCESS}; font-size: 12px;"
        )
        self._refresh_label.setVisible(False)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(3000)
        self._refresh_timer.timeout.connect(lambda: self._refresh_label.setVisible(False))

    def create_layout(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 0, 10, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.items_label)
        self.main_layout.addStretch()
        self.main_layout.addWidget(self._refresh_label)
        self.main_layout.addSpacing(16)
        self.main_layout.addWidget(self.selected_label)

    def create_connections(self):
        pass

    def update_items(self, count):
        self.items_label.setText(f"Items: {count}")
        self.selected_label.setText("Selected: 0")

    def update_selection(self, count):
        self.selected_label.setText(f"Selected: {count}")

    def flash_auto_refresh(self):
        """Show a brief '↻ Auto-refreshed HH:MM' message in the footer."""
        now = datetime.datetime.now().strftime("%H:%M")
        self._refresh_label.setText(f"↻  Auto-refreshed  {now}   ")
        self._refresh_label.setVisible(True)
        self._refresh_timer.start()   # restart if already running


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from core.styles import styleSheet, qt_argv
    app = QApplication(qt_argv())
    app.setStyle("Fusion")
    app.setStyleSheet(styleSheet)
    w = FooterWidget()
    w.show()
    sys.exit(app.exec_())

