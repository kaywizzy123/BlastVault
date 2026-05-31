"""
review_session_dialog.py
────────────────────────
Full review viewer for a single session.

Displays each submitted shot as a card with:
  • filename, submitter, submission note
  • review status chip
  • Play button (opens in BlastPlayer)
  • Admin-only Approve / Revision / Hold action buttons

Usage
-----
    dlg = ReviewSessionDialog(session_path, parent=self)
    dlg.exec_()
"""
import datetime
import subprocess
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QTextEdit, QSizePolicy,
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon

from core import constants
from core.reviews import read_session, write_session, set_item_review, mark_completed
from core.meta import read_meta, write_meta
from core.notes import add_note


# ── Colour map for review statuses ────────────────────────────────────────── #
_REVIEW_STATUS_COLORS = {
    "Approved":  constants.SUCCESS,
    "Revision":  "#e5a820",   # amber
    "On Hold":   constants.FAIL,
    "":          constants.TEXT_SEC,
}


class ReviewSessionDialog(QDialog):
    """Full review viewer for the session at *session_path*."""

    # Emitted after a review status is written: (file_path, new_status)
    item_reviewed = pyqtSignal(str, str)

    def __init__(self, session_path: str, parent=None):
        super().__init__(parent)
        self._session_path = session_path

        self.setWindowTitle("Review Session")
        self.setMinimumWidth(680)
        self.setMinimumHeight(500)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint
        )
        self.setStyleSheet(f"background-color: {constants.BORDER};")

        self._build_ui()
        self._load_session()

    # ------------------------------------------------------------------ #
    #  UI scaffold                                                         #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(24, 20, 24, 20)
        self._outer.setSpacing(12)

        # ── Header placeholder (filled in _load_session) ──────────────────
        self._header_widget = QWidget()
        self._header_widget.setStyleSheet("background: transparent;")
        self._header_layout = QVBoxLayout(self._header_widget)
        self._header_layout.setContentsMargins(0, 0, 0, 0)
        self._header_layout.setSpacing(4)
        self._outer.addWidget(self._header_widget)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {constants.SPLITTER_COLOR};")
        self._outer.addWidget(sep)

        # ── Shot card list ────────────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background: transparent; border: none; }}"
        )

        self._cards_container = QWidget()
        self._cards_container.setStyleSheet("background: transparent;")
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch()

        self._scroll.setWidget(self._cards_container)
        self._outer.addWidget(self._scroll, stretch=1)

        # ── Empty state ───────────────────────────────────────────────────
        self._empty_lbl = QLabel("No shots in this session yet.")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 12px; background: transparent;"
        )
        self._empty_lbl.setVisible(False)
        self._outer.addWidget(self._empty_lbl, stretch=1)

        # ── Footer ────────────────────────────────────────────────────────
        self._footer_layout = QHBoxLayout()
        self._footer_layout.setSpacing(8)
        self._outer.addLayout(self._footer_layout)

    # ------------------------------------------------------------------ #
    #  Session loading                                                     #
    # ------------------------------------------------------------------ #

    def _load_session(self):
        """Read the session JSON and rebuild the header + card list."""
        data = read_session(self._session_path)
        if not data:
            self._empty_lbl.setVisible(True)
            self._scroll.setVisible(False)
            return

        is_open    = data.get("status") == "open"
        items      = data.get("items", [])
        item_count = len(items)
        reviewed   = sum(1 for it in items if it.get("review_status"))

        # ── Rebuild header ────────────────────────────────────────────────
        _clear_layout(self._header_layout)

        try:
            date_str = datetime.date.fromisoformat(data.get("date", "")).strftime("%d %B %Y")
        except Exception:
            date_str = data.get("date", "")

        # Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        icon_lbl = QLabel()
        pix = QPixmap(str(constants.ICONS_DIR / "dashboards.png"))
        if not pix.isNull():
            icon_lbl.setPixmap(
                pix.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        icon_lbl.setStyleSheet("background: transparent;")
        title_row.addWidget(icon_lbl)

        title_lbl = QLabel(data.get("session_type", "Review Session"))
        title_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: bold;"
            f"color: {constants.TEXT_PRI}; background: transparent;"
        )
        title_row.addWidget(title_lbl, stretch=1)

        status_chip = QLabel("Open" if is_open else "Completed")
        chip_bg  = constants.SUCCESS if is_open else constants.ACCENT
        chip_col = "white" if is_open else constants.TEXT_SEC
        status_chip.setStyleSheet(f"""
            background-color: {chip_bg};
            color: {chip_col};
            border-radius: 8px;
            padding: 2px 10px;
            font-size: 11px;
            font-weight: bold;
        """)
        status_chip.setAttribute(Qt.WA_StyledBackground, True)
        title_row.addWidget(status_chip)

        self._header_layout.addLayout(title_row)

        subtitle_lbl = QLabel(
            f"{date_str}   ·   {item_count} shot{'s' if item_count != 1 else ''}"
            f"   ·   {reviewed}/{item_count} reviewed"
        )
        subtitle_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 11px; background: transparent;"
        )
        self._header_layout.addWidget(subtitle_lbl)

        # ── Rebuild card list ─────────────────────────────────────────────
        # Remove all except the trailing stretch
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not items:
            self._scroll.setVisible(False)
            self._empty_lbl.setVisible(True)
        else:
            self._scroll.setVisible(True)
            self._empty_lbl.setVisible(False)
            for it in items:
                card = self._make_card(it, is_open)
                self._cards_layout.insertWidget(
                    self._cards_layout.count() - 1, card
                )

        # ── Rebuild footer ────────────────────────────────────────────────
        _clear_layout(self._footer_layout)

        if is_open:
            complete_btn = QPushButton("Mark Session Complete")
            complete_btn.setIcon(QIcon(str(constants.ICONS_DIR / "check.png")))
            complete_btn.setIconSize(QSize(14, 14))
            complete_btn.setFixedHeight(32)
            complete_btn.setCursor(Qt.PointingHandCursor)
            complete_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {constants.ACCENT};
                    color: {constants.TEXT_SEC};
                    border: 1px solid {constants.SPLITTER_COLOR};
                    border-radius: 4px; padding: 4px 14px;
                }}
                QPushButton:hover {{
                    background-color: {constants.SUCCESS};
                    color: white; border-color: {constants.SUCCESS};
                }}
            """)
            complete_btn.clicked.connect(self._on_mark_complete)
            self._footer_layout.addWidget(complete_btn)

        self._footer_layout.addStretch()

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
        self._footer_layout.addWidget(close_btn)

    # ------------------------------------------------------------------ #
    #  Card builder                                                        #
    # ------------------------------------------------------------------ #

    def _make_card(self, item: dict, session_open: bool) -> QFrame:
        """Build a shot review card widget."""
        file_path     = item.get("file_path", "")
        submitted_by  = item.get("submitted_by", "")
        sub_note      = item.get("submission_note", "")
        review_status = item.get("review_status", "")
        reviewer_note = item.get("reviewer_note", "")
        item_id       = item.get("id", "")

        card = QFrame()
        card.setObjectName("shotCard")
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame#shotCard {{
                background-color: {constants.BG};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 6px;
            }}
            QFrame#shotCard QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(6)

        # ── Top row: filename + status chip + play btn ────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # File name (bold) — normalise separators so Windows paths display
        # correctly on macOS/Linux where \ is not a path separator.
        fname = file_path.replace("\\", "/").split("/")[-1] if file_path else "(unknown)"
        name_lbl = QLabel(fname)
        name_lbl.setStyleSheet(
            f"color: {constants.TEXT_PRI}; font-size: 13px; font-weight: bold;"
            f"background: transparent;"
        )
        name_lbl.setToolTip(file_path)
        top_row.addWidget(name_lbl, stretch=1)

        # Review status chip
        rs_color = _REVIEW_STATUS_COLORS.get(review_status, constants.TEXT_SEC)
        rs_lbl = QLabel(review_status if review_status else "Pending")
        rs_lbl.setStyleSheet(f"""
            background-color: {constants.SPLITTER_COLOR if not review_status else rs_color + '33'};
            color: {rs_color};
            border-radius: 8px;
            padding: 1px 10px;
            font-size: 11px;
            font-weight: bold;
        """)
        rs_lbl.setAttribute(Qt.WA_StyledBackground, True)
        rs_lbl.setObjectName(f"rs_chip_{item_id}")
        top_row.addWidget(rs_lbl)

        # Play button
        play_btn = QPushButton()
        play_btn.setIcon(QIcon(str(constants.ICONS_DIR / "play-button-arrowhead.png")))
        play_btn.setFixedSize(28, 28)
        play_btn.setCursor(Qt.PointingHandCursor)
        play_btn.setToolTip("Play in BlastPlayer")
        play_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {constants.ACCENT_HI};
                border-color: {constants.ACCENT_HI};
            }}
        """)
        play_btn.clicked.connect(lambda *_, fp=file_path: self._play_file(fp))
        top_row.addWidget(play_btn)

        cl.addLayout(top_row)

        # ── Submitter / note row ──────────────────────────────────────────
        sub_parts = []
        if submitted_by:
            sub_parts.append(f"by {submitted_by}")
        sub_text = "  ·  ".join(sub_parts) if sub_parts else ""

        if sub_note:
            note_lbl = QLabel(f"{sub_text}  —  {sub_note}" if sub_text else sub_note)
        elif sub_text:
            note_lbl = QLabel(sub_text)
        else:
            note_lbl = None

        if note_lbl:
            note_lbl.setStyleSheet(
                f"color: {constants.TEXT_SEC}; font-size: 11px; background: transparent;"
            )
            note_lbl.setWordWrap(True)
            cl.addWidget(note_lbl)

        # ── Reviewer note (if any) ────────────────────────────────────────
        if reviewer_note:
            rev_note_lbl = QLabel(f"📝  {reviewer_note}")
            rev_note_lbl.setStyleSheet(
                f"color: {constants.TEXT_SEC}; font-size: 11px; "
                f"font-style: italic; background: transparent;"
            )
            rev_note_lbl.setWordWrap(True)
            cl.addWidget(rev_note_lbl)

        # ── Review action buttons — always shown for open sessions, admin verified on click ──
        if session_open:
            btn_row = QHBoxLayout()
            btn_row.setSpacing(6)
            btn_row.addStretch()

            for label, color, rs in [
                ("Approve",  constants.SUCCESS, "Approved"),
                ("Revision", "#e5a820",         "Revision"),
                ("On Hold",  constants.FAIL,    "On Hold"),
            ]:
                btn = QPushButton(label)
                btn.setFixedHeight(26)
                btn.setCursor(Qt.PointingHandCursor)
                is_current = (review_status == rs)
                bg = color if is_current else constants.ACCENT
                fg = "white" if is_current else constants.TEXT_SEC
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {bg};
                        color: {fg};
                        border: 1px solid {color if is_current else constants.SPLITTER_COLOR};
                        border-radius: 4px; padding: 2px 12px; font-size: 12px;
                    }}
                    QPushButton:hover {{
                        background-color: {color};
                        color: white; border-color: {color};
                    }}
                """)
                btn.clicked.connect(
                    lambda *_, _id=item_id, _rs=rs, _rn=reviewer_note: self._on_review(
                        _id, _rs, _rn
                    )
                )
                btn_row.addWidget(btn)

            cl.addLayout(btn_row)

        return card

    # ------------------------------------------------------------------ #
    #  Slots                                                               #
    # ------------------------------------------------------------------ #

    def _play_file(self, file_path: str):
        """Open *file_path* in BlastPlayer (or the system default app)."""
        if not file_path or not Path(file_path).exists():
            return

        bp = constants.BLAST_PLAYER_PATH
        if bp and Path(str(bp)).is_file():
            try:
                subprocess.Popen(
                    [sys.executable, str(bp), file_path],
                    creationflags=0x00000008 if sys.platform == "win32" else 0,
                )
                return
            except Exception:
                pass

        # Fallback: OS default
        try:
            if sys.platform == "win32":
                subprocess.Popen(["start", "", file_path], shell=True)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", file_path])
            else:
                subprocess.Popen(["xdg-open", file_path])
        except Exception:
            pass

    def _on_review(self, item_id: str, review_status: str, existing_note: str = ""):
        """Write review status for *item_id* — requires admin."""
        if not self._require_admin():
            return

        note = self._ask_reviewer_note(review_status, existing_note)
        if note is None:          # user cancelled the note dialog
            return

        set_item_review(self._session_path, item_id, review_status, note)

        # Sync status + history back to the shot's .meta file
        data = read_session(self._session_path)
        for it in data.get("items", []):
            if it.get("id") == item_id:
                fp = it.get("file_path", "")
                if fp:
                    try:
                        meta = read_meta(Path(fp))
                        prev = meta.get("status", "")
                        meta["status"] = review_status
                        if review_status != prev:
                            history = meta.get("status_history", [])
                            history.append({
                                "status":    review_status,
                                "timestamp": datetime.datetime.now().isoformat(
                                    timespec="seconds"
                                ),
                            })
                            meta["status_history"] = history
                        write_meta(Path(fp), meta)
                        # Mirror non-empty reviewer notes into the asset's
                        # notes log so they appear in NotesDialog.
                        if note:
                            add_note(fp, constants.CURRENT_USER,
                                     f"[{review_status}]  {note}")
                        self.item_reviewed.emit(fp, review_status)
                    except Exception:
                        pass
                break

        # Reload the full dialog so all cards and counts reflect latest state
        self._load_session()

    def _ask_reviewer_note(self, status: str, existing_note: str = ""):
        """Prompt the admin for an optional reviewer note before saving a status.

        Returns the note string (may be empty) on confirm, or *None* if cancelled.
        """
        _status_colors = {
            "Approved": constants.SUCCESS,
            "Revision": "#e5a820",
            "On Hold":  constants.FAIL,
        }
        btn_color = _status_colors.get(status, constants.ACCENT_HI)

        dlg = QDialog(self)
        dlg.setWindowTitle(status)
        dlg.setAttribute(Qt.WA_StyledBackground, True)
        dlg.setStyleSheet(f"background-color: {constants.BORDER};")
        dlg.setMinimumWidth(400)

        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(20, 18, 20, 18)
        vl.setSpacing(10)

        lbl = QLabel("Reviewer note <i>(optional)</i>:")
        lbl.setStyleSheet(
            f"color: {constants.TEXT_PRI}; font-size: 12px; "
            f"background: transparent; border: none;"
        )
        vl.addWidget(lbl)

        note_edit = QTextEdit()
        note_edit.setPlaceholderText("Add a note for the artist…")
        note_edit.setFixedHeight(80)
        note_edit.setPlainText(existing_note)
        note_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {constants.BG};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
            }}
        """)
        vl.addWidget(note_edit)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(30)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT};
                color: {constants.TEXT_SEC};
                border: none; border-radius: 4px; padding: 2px 14px;
            }}
            QPushButton:hover {{
                background-color: {constants.SPLITTER_COLOR};
                color: {constants.TEXT_PRI};
            }}
        """)
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)

        confirm_btn = QPushButton(status)
        confirm_btn.setFixedHeight(30)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_color};
                color: white; border: none; border-radius: 4px;
                padding: 2px 14px; font-weight: bold;
            }}
            QPushButton:hover {{ opacity: 0.85; }}
        """)
        confirm_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(confirm_btn)

        vl.addLayout(btn_row)

        if dlg.exec_() == QDialog.Accepted:
            return note_edit.toPlainText().strip()
        return None

    def _on_mark_complete(self):
        if not self._require_admin():
            return
        mark_completed(self._session_path)
        self._load_session()

    # ------------------------------------------------------------------ #
    #  Admin gate                                                          #
    # ------------------------------------------------------------------ #

    def _require_admin(self) -> bool:
        """Return True if admin is unlocked, or after successful PIN verification.

        Lets admin actions be triggered directly from this dialog without
        needing to unlock via the main window header first.
        """
        if not constants.STATUS_LOCKED:
            return True

        import hashlib
        from dialogs.pin_dialog import PinInputDialog, PinSetupDialog

        if not constants.ADMIN_PIN_HASH:
            dlg = PinSetupDialog(self)
            pin, ok = dlg.get_pin()
            if not ok or not pin:
                return False
            constants.ADMIN_PIN_HASH = hashlib.sha256(pin.encode()).hexdigest()
            from core.config import save_config
            save_config()
        else:
            def _verify(pin: str) -> bool:
                return hashlib.sha256(pin.encode()).hexdigest() == constants.ADMIN_PIN_HASH

            dlg = PinInputDialog(verify_fn=_verify, parent=self)
            _, ok = dlg.get_pin()
            if not ok:
                return False

        constants.STATUS_LOCKED = False
        return True


# ── Utility ───────────────────────────────────────────────────────────────── #

def _clear_layout(layout):
    """Remove and delete all items from *layout*."""
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear_layout(item.layout())
