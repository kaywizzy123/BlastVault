"""Full-resolution zoomable image viewer dialog.

Scroll-wheel zooms in / out.  Esc closes.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QLabel, QSizePolicy
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap

from core import constants


class _ZoomLabel(QLabel):
    """QLabel that zooms its pixmap on mouse-wheel events."""

    _MIN_SCALE = 0.05
    _MAX_SCALE = 10.0

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._orig   = pixmap
        self._scale  = 1.0
        self.setAlignment(Qt.AlignCenter)
        self._redraw()

    def wheelEvent(self, event):
        factor    = 1.1 if event.angleDelta().y() > 0 else 0.9
        new_scale = max(self._MIN_SCALE, min(self._MAX_SCALE, self._scale * factor))
        if new_scale != self._scale:
            self._scale = new_scale
            self._redraw()
        event.accept()

    def _redraw(self):
        w = max(1, int(self._orig.width()  * self._scale))
        h = max(1, int(self._orig.height() * self._scale))
        scaled = self._orig.scaled(QSize(w, h), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled)
        self.resize(scaled.size())


class ImageViewerDialog(QDialog):
    """Full-resolution, scroll-to-zoom image viewer."""

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(Path(path).name)
        self.setMinimumSize(640, 480)
        self.resize(1024, 768)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.setStyleSheet("background-color: #111111;")

        pixmap = QPixmap(path)
        if pixmap.isNull():
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.black)

        zoom_label = _ZoomLabel(pixmap, self)
        zoom_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        scroll = QScrollArea()
        scroll.setWidget(zoom_label)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setStyleSheet("background-color: #111111; border: none;")

        hint = QLabel("Scroll to zoom  ·  Esc to close")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(
            f"color: {constants.TEXT_SEC}; background: transparent;"
            f" font-size: 11px; padding: 2px 0;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(scroll)
        layout.addWidget(hint)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv + ["-platform", "windows:darkmode=1"])
    app.setStyle("Fusion")
    test = sys.argv[1] if len(sys.argv) > 1 else ""
    if test:
        dlg = ImageViewerDialog(test)
        dlg.show()
        sys.exit(app.exec_())
    else:
        print("Usage: image_viewer.py <image_path>")
        sys.exit(1)
