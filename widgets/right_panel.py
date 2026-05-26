import sys
import json
import datetime
import subprocess
from pathlib import Path

from PyQt5.QtWidgets import (
    QFormLayout, QWidget, QVBoxLayout,
    QLabel, QLineEdit, QTextEdit,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImageReader

from core import constants, styles
from core.constants import detect_department, version_key
from utils.collapsible_btn import CollapsibleWidget


# ──────────────────────────────────────────────────────────────────────────── #
#  Module-level helpers                                                         #
# ──────────────────────────────────────────────────────────────────────────── #

def _readonly_field(height: int = 25) -> QLineEdit:
    """Return a read-only, non-focusable QLineEdit."""
    field = QLineEdit()
    field.setReadOnly(True)
    field.setFocusPolicy(Qt.NoFocus)
    field.setFixedHeight(height)
    return field


# ──────────────────────────────────────────────────────────────────────────── #
#  RightPanel                                                                   #
# ──────────────────────────────────────────────────────────────────────────── #

class RightPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet(styles.input_style())
        self.create_widgets()
        self.create_layout()

    # ------------------------------------------------------------------ #
    #  Widget / layout construction                                        #
    # ------------------------------------------------------------------ #

    def create_widgets(self):
        # File Details fields
        self.file_details       = _readonly_field()
        self.department_details = _readonly_field()
        self.artist_details     = _readonly_field()
        self.version_details    = _readonly_field()
        self.date_details       = _readonly_field()
        self.file_path_details  = _readonly_field()

        self.description_details = QTextEdit()
        self.description_details.setReadOnly(True)
        self.description_details.setFocusPolicy(Qt.NoFocus)
        self.description_details.setFixedHeight(100)

        # Media Details fields
        self.resolution_details = _readonly_field()
        self.length_details     = _readonly_field()
        self.frame_details      = _readonly_field()

        # Collapsible sections (forms assembled in create_layout)
        self.file_details_widget  = CollapsibleWidget("File Details")
        self.file_details_widget.set_expanded(True)
        self.media_details_widget = CollapsibleWidget("Media Details")

    def create_layout(self):
        # ── File Details form ────────────────────────────────────────────
        info_form = QFormLayout()
        info_form.setContentsMargins(10, 4, 10, 4)
        info_form.setSpacing(4)
        for label_text, widget in (
            ("File Name:",   self.file_details),
            ("Department:",  self.department_details),
            ("Artist:",      self.artist_details),
            ("Version:",     self.version_details),
            ("Created:",     self.date_details),
            ("Description:", self.description_details),
            ("File Path:",   self.file_path_details),
        ):
            info_form.addRow(QLabel(label_text), widget)
        self.file_details_widget.add_layout(info_form)

        # ── Media Details form ───────────────────────────────────────────
        media_form = QFormLayout()
        media_form.setContentsMargins(10, 4, 10, 4)
        media_form.setSpacing(4)
        for label_text, widget in (
            ("Resolution:", self.resolution_details),
            ("Length:",     self.length_details),
            ("Frames:",     self.frame_details),
        ):
            media_form.addRow(QLabel(label_text), widget)
        self.media_details_widget.add_layout(media_form)

        # ── Content container (hidden until a file is selected) ──────────
        self.content_widget = QWidget()
        self.content_widget.hide()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.file_details_widget)
        content_layout.addWidget(self.media_details_widget)
        content_layout.addStretch()

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.content_widget)
        self.main_layout.addStretch()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def display_metadata(self, path: str):
        """Populate the panel with metadata for *path*. Clears if empty/invalid."""
        if not path:
            self._clear()
            return

        p = Path(path)
        if not p.is_file():
            self._clear()
            return

        base, ver = version_key(p.stem)
        self.file_details.setText(base if base is not None else p.stem)
        self.version_details.setText(str(ver) if ver is not None else "")
        self.file_path_details.setText(str(p))
        self.department_details.setText(detect_department(p.name))
        self.artist_details.clear()

        try:
            ctime = p.stat().st_birthtime
            self.date_details.setText(
                datetime.datetime.fromtimestamp(ctime).strftime("%Y-%m-%d  %H:%M:%S")
            )
        except OSError:
            self.date_details.clear()

        sidecar = p.with_suffix(".txt")
        if sidecar.exists():
            try:
                self.description_details.setText(sidecar.read_text(encoding="utf-8"))
            except Exception:
                self.description_details.clear()
        else:
            self.description_details.clear()

        self.resolution_details.clear()
        self.length_details.clear()
        self.frame_details.clear()

        ext = p.suffix.lower()
        if ext in constants.IMAGE_EXTS:
            reader = QImageReader(str(p))
            size = reader.size()
            if size.isValid():
                self.resolution_details.setText(f"{size.width()} x {size.height()}")
        elif ext in constants.VIDEO_EXTS:
            self._read_video_metadata(str(p))

        self.content_widget.show()

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _clear(self):
        """Clear all fields and hide the content panel."""
        for field in (
            self.file_details, self.department_details, self.artist_details,
            self.version_details, self.date_details, self.file_path_details,
            self.resolution_details, self.length_details, self.frame_details,
        ):
            field.clear()
        self.description_details.clear()
        self.content_widget.hide()

    def _read_video_metadata(self, path: str):
        """Populate resolution / length / frame fields via ffprobe."""
        ffprobe = str(Path(constants.FFMPEG_PATH).parent / "ffprobe.exe")
        if not Path(ffprobe).exists():
            return
        try:
            result = subprocess.run(
                [ffprobe, "-v", "quiet", "-print_format", "json",
                 "-show_streams", "-show_format", path],
                capture_output=True, text=True, timeout=10,
            )
            data = json.loads(result.stdout)
        except Exception:
            return

        for stream in data.get("streams", []):
            if stream.get("codec_type") != "video":
                continue

            w, h = stream.get("width"), stream.get("height")
            if w and h:
                self.resolution_details.setText(f"{w} x {h}")

            nb = stream.get("nb_frames", "")
            if nb and nb != "N/A":
                self.frame_details.setText(f"{nb} frames")

            dur = stream.get("duration") or data.get("format", {}).get("duration")
            if dur:
                try:
                    total   = float(dur)
                    ms      = int(round((total % 1) * 1000))
                    total_s = int(total)
                    mins, s = divmod(total_s, 60)
                    hrs,  m = divmod(mins, 60)
                    self.length_details.setText(f"{hrs:02d}:{m:02d}:{s:02d}:{ms:03d}")
                except ValueError:
                    pass
            break


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from PyQt5.QtWidgets import QApplication
    from core.styles import styleSheet
    app = QApplication(sys.argv + ["-platform", "windows:darkmode=1"])
    app.setStyle("Fusion")
    app.setStyleSheet(styleSheet)
    w = RightPanel()
    w.resize(300, 600)
    w.show()
    sys.exit(app.exec_())
