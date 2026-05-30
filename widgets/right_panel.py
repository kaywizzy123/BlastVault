import sys
import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QFormLayout, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton,
)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QImageReader, QIcon

from core import constants, styles
from core.constants import detect_department, detect_artist, version_key, file_ctime
from core.meta import read_meta_with_fallback, read_meta, write_meta
from core.probe import probe_video, fmt_duration, fmt_resolution, fmt_fps, fmt_bitrate
from utils.collapsible_btn import CollapsibleWidget


# ──────────────────────────────────────────────────────────────────────────── #
#  Background probe worker                                                      #
# ──────────────────────────────────────────────────────────────────────────── #

class ProbeWorker(QThread):
    """Run ``probe_video()`` in a background thread so the UI stays responsive.

    Emits ``probe_ready(path, info)`` on completion unless ``cancel()`` was
    called first.  Old workers are never waited on — they finish naturally
    and their result is simply discarded.
    """
    probe_ready = pyqtSignal(str, dict)

    def __init__(self, path: str):
        super().__init__()
        self._path      = path
        self._cancelled = False

    def cancel(self):
        """Mark this worker as cancelled; its result will be discarded."""
        self._cancelled = True

    def run(self):
        info = probe_video(self._path)
        if not self._cancelled:
            self.probe_ready.emit(self._path, info)


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


def _fmt_size(n: int) -> str:
    """Return a human-readable file size string (e.g. '3.2 MB')."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


# ──────────────────────────────────────────────────────────────────────────── #
#  RightPanel                                                                   #
# ──────────────────────────────────────────────────────────────────────────── #

class RightPanel(QWidget):
    # Emitted when the user changes the status via the right-panel combo.
    # Carries (absolute_path_str, new_status_str) so the center panel can
    # update its badge without a full reload.
    status_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet(styles.input_style())
        self._current_path = None   # Path of the file currently displayed
        self._probe_worker = None   # background ffprobe thread
        self.create_widgets()
        self.create_layout()

    # ------------------------------------------------------------------ #
    #  Widget / layout construction                                        #
    # ------------------------------------------------------------------ #

    def create_widgets(self):
        # ── File Details fields ──────────────────────────────────────────
        self.file_details       = _readonly_field()
        self.department_details = _readonly_field()
        self.artist_details     = _readonly_field()
        self.version_details    = _readonly_field()
        self.date_details       = _readonly_field()
        self.file_size_details  = _readonly_field()
        self.file_path_details  = _readonly_field()

        self.description_details = QTextEdit()
        self.description_details.setReadOnly(True)
        self.description_details.setFocusPolicy(Qt.NoFocus)
        self.description_details.setFixedHeight(100)

        # ── Status badge + dropdown ──────────────────────────────────────
        # Badge: small coloured dot that mirrors the selected status colour
        self.status_badge = QLabel()
        self.status_badge.setFixedSize(10, 10)
        self._set_status_badge_color("")   # grey (no status) on init

        # Combo: all five status options; blank "—" means no status set
        self.status_combo = QComboBox()
        self.status_combo.addItem("Clear Status")
        self.status_combo.addItems(constants.STATUS_OPTIONS)
        self.status_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px;
                padding: 2px 6px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                selection-background-color: {constants.ACCENT};
            }}
            QComboBox::drop-down {{ border: none; width: 18px; }}
        """)
        self.status_combo.currentTextChanged.connect(self._on_status_changed)

        # Container widget that holds badge + combo in one row
        self._status_row_widget = QWidget()
        self._status_row_widget.setStyleSheet("background: transparent;")
        _sr = QHBoxLayout(self._status_row_widget)
        _sr.setContentsMargins(0, 0, 0, 0)
        _sr.setSpacing(6)
        _sr.addWidget(self.status_badge)
        _sr.addWidget(self.status_combo)
        _sr.addStretch()

        # ── Media Details fields ─────────────────────────────────────────
        self.resolution_details = _readonly_field()
        self.fps_details        = _readonly_field()
        self.codec_details      = _readonly_field()
        self.audio_details      = _readonly_field()
        self.bitrate_details    = _readonly_field()
        self.length_details     = _readonly_field()
        self.frame_details      = _readonly_field()

        # ── Collapsible sections (forms assembled in create_layout) ──────
        self.file_details_widget  = CollapsibleWidget("File Details")
        self.file_details_widget.set_expanded(True)
        self.media_details_widget = CollapsibleWidget("Media Details")
        self.media_details_widget.set_expanded(True)

    def create_layout(self):
        # ── File Details form ────────────────────────────────────────────
        info_form = QFormLayout()
        info_form.setContentsMargins(10, 4, 10, 4)
        info_form.setSpacing(4)
        self._status_label = QLabel("Status:")
        for label_text, widget in (
            ("File Name:",   self.file_details),
            (self._status_label, self._status_row_widget),
            ("Department:",  self.department_details),
            ("Artist:",      self.artist_details),
            ("Version:",     self.version_details),
            ("Created:",     self.date_details),
            ("File Size:",   self.file_size_details),
            ("Description:", self.description_details),
            ("File Path:",   self.file_path_details),
        ):
            if isinstance(label_text, str):
                info_form.addRow(QLabel(label_text), widget)
            else:
                info_form.addRow(label_text, widget)
        self.file_details_widget.add_layout(info_form)

        # ── Media Details form ───────────────────────────────────────────
        media_form = QFormLayout()
        media_form.setContentsMargins(10, 4, 10, 4)
        media_form.setSpacing(4)
        for label_text, widget in (
            ("Resolution:", self.resolution_details),
            ("FPS:",        self.fps_details),
            ("Codec:",      self.codec_details),
            ("Audio:",      self.audio_details),
            ("Bit Rate:",   self.bitrate_details),
            ("Duration:",   self.length_details),
            ("Frames:",     self.frame_details),
        ):
            media_form.addRow(QLabel(label_text), widget)
        self.media_details_widget.add_layout(media_form)

        # ── Notes button ─────────────────────────────────────────────────
        self.notes_btn = QPushButton()
        self.notes_btn.setIcon(QIcon(str(constants.ICONS_DIR / "add_note.png")))
        self.notes_btn.setIconSize(QSize(18, 18))
        self.notes_btn.setFixedSize(28, 28)
        self.notes_btn.setCursor(Qt.PointingHandCursor)
        self.notes_btn.setToolTip("Notes")
        self.notes_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {constants.ACCENT_HI};
                border: 1px solid {constants.ACCENT_HI};
            }}
        """)
        self.notes_btn.clicked.connect(self._on_notes_clicked)

        # ── Content container (hidden until a file is selected) ──────────
        self.content_widget = QWidget()
        self.content_widget.hide()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(4, 4, 12, 12)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.file_details_widget)
        content_layout.addWidget(self.media_details_widget)
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 4, 10, 0)
        btn_row.addStretch()
        btn_row.addWidget(self.notes_btn)
        content_layout.addLayout(btn_row)
        content_layout.addStretch()

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.content_widget)
        self.main_layout.addStretch()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def set_status_locked(self, locked: bool):
        """Toggle between supervisor combo and artist submit button."""
        self.status_combo.setEnabled(not locked)
        self.status_combo.setToolTip(
            "Status locked  —  unlock via the padlock in the header" if locked else ""
        )

    def set_seq_mode(self, is_seq: bool):
        """Hide the status row when showing a SEQ-level item."""
        self._status_label.setVisible(not is_seq)
        self._status_row_widget.setVisible(not is_seq)

    def display_metadata(self, path: str):
        """Populate the panel with metadata for *path*. Clears if empty/invalid."""
        if not path:
            self._clear()
            return

        p = Path(path)
        if not p.is_file():
            self._clear()
            return

        # ── Structured metadata: .meta → .txt sidecar → filename fallback ──
        meta = read_meta_with_fallback(p)

        base, ver = version_key(p.stem)
        self.file_details.setText(base if base is not None else p.stem)

        # Version: prefer meta, fall back to filename parse
        meta_ver = meta.get("version")
        if meta_ver is not None:
            self.version_details.setText(str(meta_ver))
        else:
            self.version_details.setText(str(ver) if ver is not None else "")

        self.file_path_details.setText(str(p))

        # Department: prefer meta, fall back to filename token detection
        self.department_details.setText(
            meta.get("department") or detect_department(p.name)
        )

        # Artist: meta → filename convention fallback
        self.artist_details.setText(meta.get("artist") or detect_artist(p.name))

        try:
            ctime = file_ctime(p)
            self.date_details.setText(
                datetime.datetime.fromtimestamp(ctime).strftime("%Y-%m-%d  %H:%M:%S")
            )
        except OSError:
            self.date_details.clear()

        try:
            self.file_size_details.setText(_fmt_size(p.stat().st_size))
        except OSError:
            self.file_size_details.clear()

        # Description: raw .txt content when present (preserves full text);
        # fall back to the "description" field parsed from the sidecar by
        # read_meta_with_fallback (strips key:value lines already consumed).
        sidecar = p.with_suffix(".txt")
        if sidecar.exists():
            try:
                self.description_details.setText(sidecar.read_text(encoding="utf-8"))
            except Exception:
                self.description_details.clear()
        elif meta.get("description"):
            self.description_details.setText(meta["description"])
        else:
            self.description_details.clear()

        # ── Status ──────────────────────────────────────────────────────
        status = meta.get("status", "")
        self.status_combo.blockSignals(True)
        idx = self.status_combo.findText(status)
        self.status_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.status_combo.blockSignals(False)
        self._set_status_badge_color(status)

        # ── Media metadata ───────────────────────────────────────────────
        for field in (self.resolution_details, self.fps_details, self.codec_details,
                      self.audio_details, self.bitrate_details,
                      self.length_details, self.frame_details):
            field.clear()

        ext = p.suffix.lower()
        if ext in constants.IMAGE_EXTS:
            reader = QImageReader(str(p))
            size = reader.size()
            if size.isValid():
                self.resolution_details.setText(f"{size.width()} × {size.height()}")

        elif ext in constants.VIDEO_EXTS:
            # Show "—" placeholders immediately; probe runs in background
            for field in (self.resolution_details, self.fps_details,
                          self.codec_details, self.audio_details,
                          self.bitrate_details, self.length_details,
                          self.frame_details):
                field.setText("—")
            self._start_probe(str(p))

        self._current_path = p
        self.content_widget.show()

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _clear(self):
        """Clear all fields and hide the content panel."""
        # Cancel any in-flight probe so its result is not painted onto the next file
        if self._probe_worker is not None:
            self._probe_worker.cancel()
            self._probe_worker = None
        for field in (
            self.file_details, self.department_details, self.artist_details,
            self.version_details, self.date_details, self.file_size_details,
            self.file_path_details, self.resolution_details, self.fps_details,
            self.codec_details, self.audio_details, self.bitrate_details,
            self.length_details, self.frame_details,
        ):
            field.clear()
        self.description_details.clear()
        self.status_combo.blockSignals(True)
        self.status_combo.setCurrentIndex(0)
        self.status_combo.blockSignals(False)
        self._set_status_badge_color("")
        self._current_path = None
        self.content_widget.hide()

    # ------------------------------------------------------------------ #
    #  Background probe helpers                                            #
    # ------------------------------------------------------------------ #

    def _start_probe(self, path: str):
        """Cancel any running probe and launch a fresh one for *path*."""
        if self._probe_worker is not None:
            self._probe_worker.cancel()
            # Thread finishes naturally; result discarded via _cancelled flag
        self._probe_worker = ProbeWorker(path)
        self._probe_worker.probe_ready.connect(self._on_probe_ready)
        self._probe_worker.start()

    def _on_probe_ready(self, path: str, info: dict):
        """Populate media fields once the background probe completes.

        Stale results (user already moved to another file) are silently dropped.
        """
        if self._current_path is None or str(self._current_path) != path:
            return

        res = fmt_resolution(info)
        self.resolution_details.setText(res if res else "")

        self.fps_details.setText(fmt_fps(info["fps"]) if "fps" in info else "")
        self.codec_details.setText(info.get("codec", ""))
        self.audio_details.setText(info.get("audio_codec", ""))
        self.bitrate_details.setText(
            fmt_bitrate(info["bit_rate"]) if "bit_rate" in info else ""
        )
        self.length_details.setText(
            fmt_duration(info["duration"]) if "duration" in info else ""
        )
        if "nb_frames" in info:
            self.frame_details.setText(f"{info['nb_frames']:,} frames")
        else:
            self.frame_details.clear()

    def _on_notes_clicked(self):
        """Open the notes dialog for the currently displayed file."""
        if self._current_path is None:
            return
        from dialogs.notes_dialog import NotesDialog
        NotesDialog(str(self._current_path), parent=self).exec_()

    def _on_status_changed(self, status: str):
        """Write the selected status to the .meta file immediately."""
        p = getattr(self, "_current_path", None)
        if p is None:
            return
        self._set_status_badge_color(status)
        try:
            # Merge with any existing meta so other fields are preserved
            data = read_meta(p)
            if status and status != "Clear Status":
                data["status"] = status
            else:
                data.pop("status", None)
            write_meta(p, data)
        except Exception as e:
            print(f"[RightPanel] Could not save status: {e}")
        # Notify the center panel so its badge updates without a reload
        effective = status if status != "Clear Status" else ""
        self.status_changed.emit(str(p), effective)

    def _set_status_badge_color(self, status: str):
        """Paint the badge dot in the colour for *status*."""
        color = constants.STATUS_COLORS.get(status, constants.TEXT_SEC)
        self.status_badge.setStyleSheet(
            f"background-color: {color}; border-radius: 5px;"
        )



if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from PyQt5.QtWidgets import QApplication
    from core.styles import styleSheet, qt_argv
    app = QApplication(qt_argv())
    app.setStyle("Fusion")
    app.setStyleSheet(styleSheet)
    w = RightPanel()
    w.resize(300, 600)
    w.show()
    sys.exit(app.exec_())

