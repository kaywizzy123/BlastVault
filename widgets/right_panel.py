import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import QFormLayout, QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImageReader
import re
import json
import datetime
import subprocess
from pathlib import Path
from core import constants, styles
from core.constants import detect_department
from utils.collapsible_btn import CollapsibleWidget

_VERSION_RE = re.compile(r'_v(\d+)$', re.IGNORECASE)

def _version_key(stem):
    m = _VERSION_RE.search(stem)
    if m:
        return stem[:m.start()], int(m.group(1))
    return None, None



class RightPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet(styles.input_style())

    def create_widgets(self):
        self.file_label = QLabel("File Name:")
        self.file_details = QLineEdit()
        self.file_details.setReadOnly(True)
        self.file_details.setFocusPolicy(Qt.NoFocus)
        self.file_details.setFixedHeight(25)
        

        self.department_label = QLabel("Department:")
        self.department_details = QLineEdit()
        self.department_details.setReadOnly(True)
        self.department_details.setFocusPolicy(Qt.NoFocus)
        self.department_details.setFixedHeight(25)
        
        self.artist_label = QLabel("Artist:")
        self.artist_details = QLineEdit()
        self.artist_details.setReadOnly(True)
        self.artist_details.setFocusPolicy(Qt.NoFocus)
        self.artist_details.setFixedHeight(25)

        self.version_label = QLabel("Version:")
        self.version_details = QLineEdit()
        self.version_details.setReadOnly(True)
        self.version_details.setFocusPolicy(Qt.NoFocus)
        self.version_details.setFixedHeight(25)

        self.date_label = QLabel("Created:")
        self.date_details = QLineEdit()
        self.date_details.setReadOnly(True)
        self.date_details.setFocusPolicy(Qt.NoFocus)
        self.date_details.setFixedHeight(25)

        self.description_label = QLabel("Description:")
        self.description_details = QTextEdit()
        self.description_details.setReadOnly(True)
        self.description_details.setFocusPolicy(Qt.NoFocus)
        self.description_details.setFixedHeight(100)
        
        self.file_path_label = QLabel("File Path:")
        self.file_path_details = QLineEdit()
        self.file_path_details.setReadOnly(True)
        self.file_path_details.setFocusPolicy(Qt.NoFocus)
        self.file_path_details.setFixedHeight(25)
        
        self.resolution_label = QLabel("Resolution:")
        self.resolution_details = QLineEdit()
        self.resolution_details.setReadOnly(True)
        self.resolution_details.setFocusPolicy(Qt.NoFocus)
        self.resolution_details.setFixedHeight(25)
        
        self.length_label = QLabel("Length:")
        self.length_details = QLineEdit()
        self.length_details.setReadOnly(True)
        self.length_details.setFocusPolicy(Qt.NoFocus)
        self.length_details.setFixedHeight(25)
        
        self.frame_label = QLabel("Frames:")
        self.frame_details = QLineEdit()
        self.frame_details.setReadOnly(True)
        self.frame_details.setFocusPolicy(Qt.NoFocus)
        self.frame_details.setFixedHeight(25)

        self.file_details_widget = CollapsibleWidget("File Details")
        self.file_details_widget.set_expanded(True)

        self.media_details_widget = CollapsibleWidget("Media Details")
        media_form = QFormLayout()
        media_form.setContentsMargins(10, 4, 10, 4)
        media_form.setSpacing(4)
        media_form.addRow(self.resolution_label, self.resolution_details)
        media_form.addRow(self.length_label, self.length_details)
        media_form.addRow(self.frame_label, self.frame_details)
        self.media_details_widget.add_layout(media_form)
        

    def create_layout(self):
        info_layout = QFormLayout()
        info_layout.setContentsMargins(10, 4, 10, 4)
        info_layout.setSpacing(4)
        info_layout.addRow(self.file_label, self.file_details)
        info_layout.addRow(self.department_label, self.department_details)
        info_layout.addRow(self.artist_label, self.artist_details)
        info_layout.addRow(self.version_label, self.version_details)
        info_layout.addRow(self.date_label, self.date_details)
        info_layout.addRow(self.description_label, self.description_details)
        info_layout.addRow(self.file_path_label, self.file_path_details)
        self.file_details_widget.add_layout(info_layout)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4,4,4,4)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.file_details_widget)
        self.main_layout.addWidget(self.media_details_widget)
        self.main_layout.addStretch()

    def create_connections(self):
        pass

    # ------------------------------------------------------------------ #
    #  Metadata display                                                    #
    # ------------------------------------------------------------------ #

    def display_metadata(self, path):
        if not path:
            self.clear_fields()
            return

        p = Path(path)
        if not p.is_file():
            self.clear_fields()
            return

        # File name (version stripped)
        base, version = _version_key(p.stem)
        self.file_details.setText(base if base is not None else p.stem)

        # Version
        self.version_details.setText(str(version) if version is not None else "")

        # Full path
        self.file_path_details.setText(str(p))

        # Created date
        try:
            ctime = p.stat().st_ctime
            self.date_details.setText(
                datetime.datetime.fromtimestamp(ctime).strftime("%Y-%m-%d  %H:%M:%S")
            )
        except OSError:
            self.date_details.clear()

        # Department — detected from filename tokens
        self.department_details.setText(detect_department(p.name))
        self.artist_details.clear()

        # Description — look for a sidecar .txt with the same stem
        sidecar = p.with_suffix(".txt")
        if sidecar.exists():
            try:
                self.description_details.setText(sidecar.read_text(encoding="utf-8"))
            except Exception:
                self.description_details.clear()
        else:
            self.description_details.clear()

        # Media metadata
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

    def _read_video_metadata(self, path):
        ffprobe = str(Path(constants.FFMPEG_PATH).parent / "ffprobe.exe")
        if not Path(ffprobe).exists():
            return
        try:
            result = subprocess.run(
                [ffprobe, "-v", "quiet", "-print_format", "json",
                 "-show_streams", "-show_format", path],
                capture_output=True, text=True, timeout=10
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
                    total = float(dur)
                    ms = int(round((total % 1) * 1000))
                    total_s = int(total)
                    mins, s = divmod(total_s, 60)
                    hrs, m = divmod(mins, 60)
                    self.length_details.setText(
                        f"{hrs:02d}:{m:02d}:{s:02d}:{ms:03d}"
                    )
                except ValueError:
                    pass
            break

    def clear_fields(self):
        for field in (
            self.file_details, self.department_details, self.artist_details,
            self.version_details, self.date_details, self.file_path_details,
            self.resolution_details, self.length_details, self.frame_details,
        ):
            field.clear()
        self.description_details.clear()


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
