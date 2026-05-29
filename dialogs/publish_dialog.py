import sys
import getpass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QTextEdit,
    QPushButton, QFileDialog, QFrame,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap

from core import constants
from core.constants import detect_department, detect_artist, canonical_stem, version_key
from core.meta import read_meta, write_meta
from core.styles import input_style


class PublishDialog(QDialog):
    """Artist-facing publish dialog.

    Writes a ``.meta`` JSON file alongside the asset so BlastVault (and any
    other tool in the pipeline) can read structured metadata without opening
    the file.

    Version is never shown to the artist — it is computed automatically by
    scanning the asset's parent folder for sibling files with the same
    canonical stem and incrementing the highest version found by one.

    Usage from a DCC
    ----------------
    ::

        from dialogs.publish_dialog import PublishDialog
        dlg = PublishDialog("/path/to/char_hero_anim_oogunremi_v010.ma")
        dlg.exec_()

    Usage standalone
    ----------------
    ::

        python publish_dialog.py /path/to/file.ma
    """

    published = pyqtSignal(str)   # emits the asset path on successful publish

    def __init__(self, path: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Publish Asset")
        self.setFixedSize(480, 460)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._path = path
        self.create_widgets()
        self.create_layout()
        self.create_connections()

        if path:
            self._populate_from_path(path)

    # ------------------------------------------------------------------ #
    #  Widget construction                                                 #
    # ------------------------------------------------------------------ #

    def create_widgets(self):
        # ── Header ────────────────────────────────────────────────────────
        pix = QPixmap(constants.ICON)
        self._logo = QLabel()
        self._logo.setStyleSheet("background: transparent;")
        if not pix.isNull():
            self._logo.setPixmap(
                pix.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        self._title = QLabel("Publish Asset")
        self._title.setStyleSheet(f"""
            background: transparent;
            color: {constants.TEXT_PRI};
            font-size: 18px;
            font-weight: bold;
        """)

        self._subtitle = QLabel("Attach metadata to this file for the pipeline.")
        self._subtitle.setStyleSheet(
            f"background: transparent; color: {constants.TEXT_SEC}; font-size: 11px;"
        )

        # ── File path ──────────────────────────────────────────────────────
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select or drag a file…")
        self.path_edit.setStyleSheet(input_style())

        self.browse_btn = QPushButton()
        self.browse_btn.setIcon(QIcon(str(constants.ICONS_DIR / "open-file.png")))
        self.browse_btn.setToolTip("Browse for file")
        self.browse_btn.setStyleSheet(self._btn_style())

        # ── Metadata fields ───────────────────────────────────────────────
        _combo_style = f"""
            QComboBox {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QComboBox:focus {{ border: 1px solid {constants.ACCENT}; }}
            QComboBox QAbstractItemView {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.BG};
                outline: none;
                selection-background-color: {constants.ACCENT};
            }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{
                image: url({str(constants.ICONS_DIR / "arrow-down-sign-to-navigate.png").replace(chr(92), "/")});
                width: 12px; height: 12px;
            }}
        """

        self.artist_combo = QComboBox()
        self.artist_combo.setEditable(True)
        self.artist_combo.addItems(constants.ARTISTS)
        self.artist_combo.setStyleSheet(_combo_style)

        self.dept_combo = QComboBox()
        self.dept_combo.addItems(
            [d for d in constants.DEPARTMENTS if d != "All"]
        )
        self.dept_combo.setStyleSheet(_combo_style)

        self.dcc_edit = QLineEdit()
        self.dcc_edit.setPlaceholderText("e.g. Maya 2025, Houdini 20, Nuke 15…")
        self.dcc_edit.setStyleSheet(input_style())

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Optional notes about this version…")
        self.notes_edit.setFixedHeight(90)
        self.notes_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px;
                padding: 4px;
            }}
            QTextEdit:focus {{ border: 1px solid {constants.ACCENT}; }}
        """)

        # ── Action buttons ─────────────────────────────────────────────────
        self.publish_btn = QPushButton("  Publish")
        self.publish_btn.setIcon(QIcon(str(constants.ICONS_DIR / "diskette.png")))
        self.publish_btn.setFixedWidth(120)
        self.publish_btn.setStyleSheet(self._btn_style(hover_color=constants.ACCENT_HI))

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.setStyleSheet(self._btn_style(hover_color=constants.FAIL))

        # ── Status label ───────────────────────────────────────────────────
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(
            f"background: transparent; color: {constants.SUCCESS}; font-size: 11px;"
        )
        self.status_lbl.setAlignment(Qt.AlignCenter)

    # ------------------------------------------------------------------ #
    #  Layout                                                              #
    # ------------------------------------------------------------------ #

    def create_layout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Header row
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        header_row.addWidget(self._logo)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(self._title)
        title_col.addWidget(self._subtitle)
        header_row.addLayout(title_col)
        header_row.addStretch()
        layout.addLayout(header_row)

        # Divider
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {constants.SPLITTER_COLOR}; margin: 0;")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # File row
        file_row = QHBoxLayout()
        file_row.addWidget(self.path_edit)
        file_row.addWidget(self.browse_btn)
        layout.addLayout(file_row)

        # Metadata form
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setContentsMargins(0, 0, 0, 0)

        label_style = (
            f"color: {constants.TEXT_SEC}; background: transparent; font-size: 12px;"
        )
        for text, widget in (
            ("Artist:",     self.artist_combo),
            ("Department:", self.dept_combo),
            ("DCC:",        self.dcc_edit),
            ("Notes:",      self.notes_edit),
        ):
            lbl = QLabel(text)
            lbl.setStyleSheet(label_style)
            form.addRow(lbl, widget)

        layout.addLayout(form)
        layout.addWidget(self.status_lbl)
        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.publish_btn)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------ #
    #  Connections                                                         #
    # ------------------------------------------------------------------ #

    def create_connections(self):
        self.browse_btn.clicked.connect(self._on_browse)
        self.path_edit.textChanged.connect(self._on_path_changed)
        self.publish_btn.clicked.connect(self._on_publish)
        self.cancel_btn.clicked.connect(self.reject)

    # ------------------------------------------------------------------ #
    #  Slots                                                               #
    # ------------------------------------------------------------------ #

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Asset File")
        if path:
            self.path_edit.setText(path)

    def _on_path_changed(self, text: str):
        if Path(text).is_file():
            self._populate_from_path(text)

    def _on_publish(self):
        path = self.path_edit.text().strip()
        if not path or not Path(path).is_file():
            self._set_status("Please select a valid file.", error=True)
            return

        artist = self.artist_combo.currentText().strip()
        dept   = self.dept_combo.currentText().strip()
        dcc    = self.dcc_edit.text().strip()
        notes  = self.notes_edit.toPlainText().strip()

        if not artist:
            self._set_status("Artist name is required.", error=True)
            return

        next_ver = self._compute_next_version(path)

        data = {
            "artist":       artist,
            "department":   dept,
            "version":      next_ver,
            "published_at": datetime.now().isoformat(timespec="seconds"),
        }
        if dcc:
            data["dcc"] = dcc
        if notes:
            data["notes"] = notes

        try:
            write_meta(Path(path), data)
        except Exception as e:
            self._set_status(f"Write failed: {e}", error=True)
            return

        self._set_status(f"Published  ✓  (v{next_ver:03d})", error=False)
        self.published.emit(path)
        # Brief pause so the artist sees the success state, then close
        QTimer.singleShot(800, self.accept)

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _compute_next_version(self, path: str) -> int:
        """Scan the parent folder for same-asset siblings and return latest + 1.

        Two files are considered the *same asset* when they share the same
        canonical stem (dept and artist tokens stripped) **and** the same
        file extension.  The highest ``_v###`` number found is incremented
        by one.  If no versioned siblings exist, returns ``1``.
        """
        p      = Path(path)
        folder = p.parent
        ext    = p.suffix.lower()

        # Canonical stem of the file being published
        base, _    = version_key(p.stem)
        stem_base  = base if base is not None else p.stem
        target_can = canonical_stem(stem_base, detect_artist(p.name))

        max_ver = 0
        try:
            for sibling in folder.iterdir():
                if not sibling.is_file():
                    continue
                if sibling.suffix.lower() != ext:
                    continue
                sib_base, sib_ver = version_key(sibling.stem)
                if sib_ver is None:
                    continue
                sib_stem  = sib_base if sib_base is not None else sibling.stem
                sib_can   = canonical_stem(sib_stem, detect_artist(sibling.name))
                if sib_can == target_can:
                    max_ver = max(max_ver, sib_ver)
        except (PermissionError, OSError):
            pass

        return max_ver + 1

    def _populate_from_path(self, path: str):
        """Pre-fill artist / department / DCC / notes from .meta or filename."""
        self._path = path
        self.path_edit.blockSignals(True)
        self.path_edit.setText(path)
        self.path_edit.blockSignals(False)

        p    = Path(path)
        meta = read_meta(p)

        # Artist: .meta → filename token → OS username
        artist = meta.get("artist") or detect_artist(p.name) or _os_username()
        idx = self.artist_combo.findText(artist)
        if idx >= 0:
            self.artist_combo.setCurrentIndex(idx)
        else:
            self.artist_combo.setEditText(artist)

        # Department: .meta → filename token
        dept = meta.get("department") or detect_department(p.name)
        idx  = self.dept_combo.findText(dept)
        if idx >= 0:
            self.dept_combo.setCurrentIndex(idx)

        # DCC and notes from existing .meta
        self.dcc_edit.setText(meta.get("dcc", ""))
        self.notes_edit.setPlainText(meta.get("notes", ""))

        self.status_lbl.clear()

    def _set_status(self, msg: str, error: bool = False):
        color = constants.FAIL if error else constants.SUCCESS
        self.status_lbl.setStyleSheet(
            f"background: transparent; color: {color}; font-size: 11px;"
        )
        self.status_lbl.setText(msg)

    @staticmethod
    def _btn_style(hover_color: str = None) -> str:
        hover = hover_color or constants.BORDER
        return f"""
            QPushButton {{
                background-color: {constants.SPLITTER_COLOR};
                color: {constants.TEXT_PRI};
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
        """


def _os_username() -> str:
    """Return the OS login name as a lowercase fallback artist identifier."""
    try:
        return getpass.getuser().lower()
    except Exception:
        return ""


# ── Standalone preview ────────────────────────────────────────────────────── #
if __name__ == "__main__":
    from core.styles import qt_argv, styleSheet
    from PyQt5.QtWidgets import QApplication

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(qt_argv())
    app.setStyle("Fusion")
    app.setStyleSheet(styleSheet)

    path = sys.argv[1] if len(sys.argv) > 1 else ""
    dlg  = PublishDialog(path)
    dlg.exec_()
    sys.exit(0)
