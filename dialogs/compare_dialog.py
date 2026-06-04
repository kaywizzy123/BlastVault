"""
compare_dialog.py
─────────────────
Side-by-side comparison viewer for two versions of the same shot.

Shows both file paths with metadata (version, submit date, review status)
and provides a Play button for each side so the reviewer can open each
version in BlastPlayer / the system default player.

Usage
-----
    dlg = CompareDialog(path_a, path_b, ver_a, ver_b, parent=self)
    dlg.exec_()
"""
import subprocess
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QWidget,
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QPixmap

from core import constants


class CompareDialog(QDialog):
    """Side-by-side viewer comparing *path_a* (newer) with *path_b* (older).

    Parameters
    ----------
    path_a : str
        Path to the **current** (newer) version.
    path_b : str
        Path to the **previous** (older) version.
    ver_a : int
        Version number of *path_a* (shown as label).
    ver_b : int
        Version number of *path_b* (shown as label).
    session_item_a : dict | None
        Optional item dict from the session for *path_a* — used to show
        extra metadata (submitted_by, review_status, reviewer_note, …).
    session_item_b : dict | None
        Optional item dict from the session for *path_b* (or version_history
        entry) — same purpose.
    """

    def __init__(
        self,
        path_a: str,
        path_b: str,
        ver_a: int = 2,
        ver_b: int = 1,
        session_item_a: dict | None = None,
        session_item_b: dict | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._path_a = path_a
        self._path_b = path_b
        self._ver_a  = ver_a
        self._ver_b  = ver_b
        self._meta_a = session_item_a or {}
        self._meta_b = session_item_b or {}

        self.setWindowTitle("Compare Versions")
        self.setMinimumWidth(780)
        self.setMinimumHeight(360)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint
        )
        self.setStyleSheet(f"background-color: {constants.BORDER};")
        self._build_ui()

    # ------------------------------------------------------------------ #
    #  UI                                                                  #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        # ── Dialog title ──────────────────────────────────────────────────
        title_row = QHBoxLayout()

        icon_lbl = QLabel()
        pix = QPixmap(str(constants.ICONS_DIR / "dashboards.png"))
        if not pix.isNull():
            icon_lbl.setPixmap(
                pix.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        icon_lbl.setStyleSheet("background: transparent;")
        title_row.addWidget(icon_lbl)

        t = QLabel("Version Comparison")
        t.setStyleSheet(
            f"font-size: 15px; font-weight: bold;"
            f"color: {constants.TEXT_PRI}; background: transparent;"
        )
        title_row.addWidget(t, stretch=1)
        outer.addLayout(title_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {constants.SPLITTER_COLOR};")
        outer.addWidget(sep)

        # ── Side-by-side panels ───────────────────────────────────────────
        panels_row = QHBoxLayout()
        panels_row.setSpacing(12)

        # Left = older version (B), Right = newer version (A)
        left_panel  = self._build_panel(
            self._path_b, self._ver_b, self._meta_b, is_current=False
        )
        right_panel = self._build_panel(
            self._path_a, self._ver_a, self._meta_a, is_current=True
        )

        panels_row.addWidget(left_panel,  stretch=1)

        # Centre divider arrow
        arrow_lbl = QLabel()
        arrow_pix = QPixmap(str(constants.ICONS_DIR / "right-arrow.png"))
        if not arrow_pix.isNull():
            arrow_lbl.setPixmap(
                arrow_pix.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        arrow_lbl.setAlignment(Qt.AlignCenter)
        arrow_lbl.setFixedWidth(28)
        arrow_lbl.setStyleSheet("background: transparent;")
        panels_row.addWidget(arrow_lbl)

        panels_row.addWidget(right_panel, stretch=1)
        outer.addLayout(panels_row, stretch=1)

        # ── Play Both row ─────────────────────────────────────────────────
        play_both_btn = QPushButton("  Play Both")
        play_both_btn.setIcon(QIcon(str(constants.ICONS_DIR / "play-button-arrowhead.png")))
        play_both_btn.setIconSize(QSize(14, 14))
        play_both_btn.setFixedHeight(32)
        play_both_btn.setCursor(Qt.PointingHandCursor)
        play_both_btn.setToolTip("Open both versions in player one after the other")
        play_both_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT_HI};
                color: white; border: none; border-radius: 4px;
                padding: 4px 18px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #1a95e8; }}
        """)
        play_both_btn.clicked.connect(self._play_both)

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT};
                color: {constants.TEXT_SEC};
                border: none; border-radius: 4px; padding: 4px 16px;
            }}
            QPushButton:hover {{
                background-color: {constants.SPLITTER_COLOR};
                color: {constants.TEXT_PRI};
            }}
        """)
        close_btn.clicked.connect(self.accept)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        footer.addStretch()
        footer.addWidget(play_both_btn)
        footer.addWidget(close_btn)
        outer.addLayout(footer)

    def _build_panel(
        self,
        file_path: str,
        version: int,
        meta: dict,
        is_current: bool,
    ) -> QWidget:
        """Build one comparison panel (left or right)."""
        exists = Path(file_path).exists() if file_path else False
        label  = "Current Version" if is_current else "Previous Version"

        panel = QFrame()
        panel.setObjectName("comparePanel")
        accent = constants.ACCENT_HI if is_current else constants.SPLITTER_COLOR
        panel.setStyleSheet(f"""
            QFrame#comparePanel {{
                background-color: {constants.BG};
                border: 1px solid {accent};
                border-radius: 6px;
            }}
            QFrame#comparePanel QLabel {{
                border: none; background: transparent;
            }}
        """)

        vl = QVBoxLayout(panel)
        vl.setContentsMargins(16, 14, 16, 14)
        vl.setSpacing(8)

        # ── Panel label ───────────────────────────────────────────────────
        lbl_row = QHBoxLayout()
        lbl_row.setSpacing(8)

        label_lbl = QLabel(label)
        label_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 11px;"
            f"font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;"
        )
        lbl_row.addWidget(label_lbl)
        lbl_row.addStretch()

        # Version badge
        ver_badge = QLabel(f"v{version}")
        ver_badge.setStyleSheet(f"""
            background-color: {accent}33;
            color: {accent};
            border-radius: 6px; padding: 1px 8px;
            font-size: 11px; font-weight: bold;
        """)
        ver_badge.setAttribute(Qt.WA_StyledBackground, True)
        lbl_row.addWidget(ver_badge)
        vl.addLayout(lbl_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {constants.SPLITTER_COLOR};")
        vl.addWidget(sep)

        # ── File name ─────────────────────────────────────────────────────
        fname = file_path.replace("\\", "/").split("/")[-1] if file_path else "(no file)"
        fname_lbl = QLabel(fname)
        fname_lbl.setStyleSheet(
            f"color: {constants.TEXT_PRI}; font-size: 13px; font-weight: bold;"
        )
        fname_lbl.setWordWrap(True)
        vl.addWidget(fname_lbl)

        # Short path — show last two components, full path in tooltip
        from pathlib import Path as _P
        if file_path:
            _parts = _P(file_path).parts
            short_path = str(_P(*_parts[-2:])) if len(_parts) >= 2 else file_path
        else:
            short_path = "—"
        path_lbl = QLabel(short_path)
        path_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 10px;"
        )
        path_lbl.setToolTip(file_path)
        vl.addWidget(path_lbl)

        # ── Metadata ──────────────────────────────────────────────────────
        sub_by   = meta.get("submitted_by", "")
        sub_at   = meta.get("submitted_at", "")[:10]
        sub_note = meta.get("submission_note", "")
        rs       = meta.get("review_status", "")
        rv_note  = meta.get("reviewer_note", "")

        _RS_COLORS = {
            "Approved": constants.SUCCESS,
            "Revision": "#e5a820",
            "On Hold":  constants.FAIL,
            "":         constants.TEXT_SEC,
        }

        if sub_by or sub_at:
            meta_parts = []
            if sub_by:
                meta_parts.append(f"by {sub_by}")
            if sub_at:
                meta_parts.append(sub_at)
            meta_lbl = QLabel("  ·  ".join(meta_parts))
            meta_lbl.setStyleSheet(
                f"color: {constants.TEXT_SEC}; font-size: 11px;"
            )
            vl.addWidget(meta_lbl)

        if sub_note:
            sn_lbl = QLabel(sub_note)
            sn_lbl.setStyleSheet(
                f"color: {constants.TEXT_SEC}; font-size: 11px;"
            )
            sn_lbl.setWordWrap(True)
            vl.addWidget(sn_lbl)

        if rs:
            rs_row = QHBoxLayout()
            rs_chip = QLabel(rs)
            rs_color = _RS_COLORS.get(rs, constants.TEXT_SEC)
            rs_chip.setStyleSheet(f"""
                background-color: {rs_color}33;
                color: {rs_color};
                border-radius: 7px; padding: 1px 10px;
                font-size: 11px; font-weight: bold;
            """)
            rs_chip.setAttribute(Qt.WA_StyledBackground, True)
            rs_row.addWidget(rs_chip)
            rs_row.addStretch()
            vl.addLayout(rs_row)

        if rv_note:
            rv_lbl = QLabel(f"📝  {rv_note}")
            rv_lbl.setStyleSheet(
                f"color: {constants.TEXT_SEC}; font-size: 11px; font-style: italic;"
            )
            rv_lbl.setWordWrap(True)
            vl.addWidget(rv_lbl)

        # Frame annotations
        for ann in meta.get("frame_annotations", []):
            start = ann.get("start", "")
            end   = ann.get("end", "")
            note  = ann.get("note", "")
            rng   = f"[{start}–{end}]" if start != "" and end != "" else ""
            ann_lbl = QLabel(f"🎞  {rng}  {note}".strip())
            ann_lbl.setStyleSheet(
                f"color: {constants.ACCENT_HI}; font-size: 11px;"
            )
            ann_lbl.setWordWrap(True)
            vl.addWidget(ann_lbl)

        vl.addStretch()

        # ── Unavailable warning ───────────────────────────────────────────
        if not exists:
            warn = QLabel("⚠  File not found on disk")
            warn.setStyleSheet(
                f"color: {constants.FAIL}; font-size: 11px;"
            )
            vl.addWidget(warn)

        # ── Play button ───────────────────────────────────────────────────
        play_btn = QPushButton()
        play_btn.setIcon(
            QIcon(str(constants.ICONS_DIR / "play-button-arrowhead.png"))
        )
        play_btn.setIconSize(QSize(14, 14))
        play_btn.setText("  Play")
        play_btn.setFixedHeight(30)
        play_btn.setCursor(Qt.PointingHandCursor)
        play_btn.setEnabled(exists)
        play_btn.setToolTip(
            "Play in BlastPlayer" if exists else "File not available"
        )
        play_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT};
                color: {constants.TEXT_SEC};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px; padding: 2px 12px; font-size: 12px;
            }}
            QPushButton:hover:enabled {{
                background-color: {constants.ACCENT_HI};
                color: white; border-color: {constants.ACCENT_HI};
            }}
            QPushButton:disabled {{
                opacity: 0.4;
            }}
        """)
        play_btn.clicked.connect(lambda *_, fp=file_path: self._play(fp))
        vl.addWidget(play_btn)

        return panel

    # ------------------------------------------------------------------ #
    #  Playback                                                            #
    # ------------------------------------------------------------------ #

    def _play(self, file_path: str):
        """Open *file_path* in BlastPlayer, or fall back to OS default."""
        from PyQt5.QtCore import QTimer
        from PyQt5.QtWidgets import QMessageBox

        if not file_path or not Path(file_path).exists():
            return
        bp = constants.BLAST_PLAYER_PATH
        if bp and Path(str(bp)).is_file():
            try:
                kwargs: dict = {
                    "stderr": subprocess.PIPE,
                    "cwd":    str(Path(str(bp)).parent),
                }
                if sys.platform == "win32":
                    kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
                proc = subprocess.Popen(
                    [sys.executable, str(bp), file_path], **kwargs
                )

                def _check():
                    if proc.poll() is not None:
                        err = proc.stderr.read().decode(errors="replace").strip()
                        msg = "BlastPlayer exited immediately."
                        if err:
                            msg += f"\n\n{err}"
                        QMessageBox.critical(self, "BlastPlayer failed to start", msg)
                QTimer.singleShot(800, _check)
                return
            except Exception as exc:
                QMessageBox.critical(self, "Could not launch BlastPlayer", str(exc))
                return

        # BlastPlayer not found — open with the OS default video handler
        try:
            if sys.platform == "win32":
                subprocess.Popen(["start", "", file_path], shell=True)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", file_path])
            else:
                subprocess.Popen(["xdg-open", file_path])
        except Exception as exc:
            QMessageBox.critical(self, "Could not open file", str(exc))

    def _play_both(self):
        """Launch both versions — older first, then newer."""
        self._play(self._path_b)
        self._play(self._path_a)
