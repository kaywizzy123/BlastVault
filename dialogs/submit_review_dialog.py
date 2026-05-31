"""
submit_review_dialog.py
───────────────────────
Dialog that lets any user submit one or more shots to an open review session.

Usage
-----
    dlg = SubmitReviewDialog(file_paths, catalog_root, parent=self)
    dlg.exec_()   # submission happens inside on accept
"""
import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QFrame, QScrollArea, QWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

from core import constants
from core.reviews import list_sessions, create_session, add_items
from core.meta import read_meta, write_meta


class SubmitReviewDialog(QDialog):
    """Submit *file_paths* to a review session inside *catalog_root*."""

    def __init__(self, file_paths: list[str], catalog_root: str, parent=None):
        super().__init__(parent)
        self._file_paths   = file_paths
        self._catalog_root = catalog_root
        self._sessions     = []          # list of open session dicts

        self.setWindowTitle("Submit for Review")
        self.setFixedWidth(460)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setStyleSheet(f"background-color: {constants.BORDER};")

        self._build_ui()
        self._load_sessions()

    # ------------------------------------------------------------------ #
    #  UI                                                                  #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(10)

        # ── Icon + title ─────────────────────────────────────────────────
        icon_lbl = QLabel()
        pix = QPixmap(str(constants.ICONS_DIR / "add_note.png"))
        if not pix.isNull():
            icon_lbl.setPixmap(
                pix.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent;")
        outer.addWidget(icon_lbl)

        title_lbl = QLabel("Submit for Review")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(
            f"font-size: 15px; font-weight: bold;"
            f"color: {constants.TEXT_PRI}; background: transparent;"
        )
        outer.addWidget(title_lbl)
        outer.addSpacing(4)

        # ── File list ─────────────────────────────────────────────────────
        n = len(self._file_paths)
        files_lbl = QLabel(
            f"Submitting {n} shot{'s' if n != 1 else ''}:"
        )
        files_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 11px; background: transparent;"
        )
        outer.addWidget(files_lbl)

        # Scrollable compact file list (capped at 4 visible rows)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumHeight(88)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: {constants.BG}; border: 1px solid {constants.SPLITTER_COLOR}; border-radius: 4px; }}
        """)
        inner = QWidget()
        inner.setStyleSheet(f"background: {constants.BG};")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(8, 4, 8, 4)
        inner_layout.setSpacing(2)
        for fp in self._file_paths:
            row = QLabel(f"• {Path(fp).name}")
            row.setStyleSheet(
                f"color: {constants.TEXT_PRI}; font-size: 12px; background: transparent;"
            )
            inner_layout.addWidget(row)
        inner_layout.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        # ── Separator ────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {constants.SPLITTER_COLOR};")
        outer.addWidget(sep)

        # ── Review Session picker ─────────────────────────────────────────
        session_lbl = QLabel("Review Session")
        session_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 11px; background: transparent;"
        )
        outer.addWidget(session_lbl)

        session_row = QHBoxLayout()
        session_row.setSpacing(8)

        self._session_combo = QComboBox()
        self._session_combo.setFixedHeight(34)
        self._session_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {constants.BG};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 13px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                selection-background-color: {constants.ACCENT};
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
        """)
        session_row.addWidget(self._session_combo, stretch=1)

        # "+ New" — always visible; lock verified on click so any admin can create a session
        self._new_session_btn = QPushButton("+ New")
        self._new_session_btn.setFixedHeight(34)
        self._new_session_btn.setCursor(Qt.PointingHandCursor)
        self._new_session_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT};
                color: {constants.TEXT_PRI};
                border: none; border-radius: 4px; padding: 4px 12px;
            }}
            QPushButton:hover {{ background-color: {constants.ACCENT_HI}; color: white; }}
        """)
        self._new_session_btn.clicked.connect(self._on_new_session)
        session_row.addWidget(self._new_session_btn)

        outer.addLayout(session_row)

        # Placeholder shown when no sessions exist
        self._no_sessions_lbl = QLabel(
            "No open sessions.  Click  + New  to create one."
        )
        self._no_sessions_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 11px;"
            f"background: transparent; padding: 2px 0px;"
        )
        self._no_sessions_lbl.setVisible(False)
        outer.addWidget(self._no_sessions_lbl)

        # ── Note (optional) ───────────────────────────────────────────────
        note_lbl = QLabel("Note  (optional)")
        note_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 11px; background: transparent;"
        )
        outer.addWidget(note_lbl)

        self._note_field = QTextEdit()
        self._note_field.setPlaceholderText("e.g.  First pass on the foot contacts")
        self._note_field.setFixedHeight(64)
        self._note_field.setStyleSheet(f"""
            QTextEdit {{
                background-color: {constants.BG};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px; padding: 6px; font-size: 12px;
            }}
            QTextEdit:focus {{ border: 1px solid {constants.ACCENT_HI}; }}
        """)
        outer.addWidget(self._note_field)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(32)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
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
        cancel_btn.clicked.connect(self.reject)

        self._submit_btn = QPushButton("Submit  →")
        self._submit_btn.setFixedHeight(32)
        self._submit_btn.setCursor(Qt.PointingHandCursor)
        self._submit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT_HI};
                color: white; border: none; border-radius: 4px;
                padding: 4px 20px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #1a95e8; }}
            QPushButton:disabled {{
                background-color: {constants.SPLITTER_COLOR};
                color: {constants.TEXT_SEC};
            }}
        """)
        self._submit_btn.clicked.connect(self._on_submit)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._submit_btn)
        outer.addLayout(btn_row)

    # ------------------------------------------------------------------ #
    #  Session loading                                                     #
    # ------------------------------------------------------------------ #

    def _load_sessions(self):
        """Populate the session combo with open sessions."""
        all_sessions = list_sessions(self._catalog_root)
        self._sessions = [s for s in all_sessions if s.get("status") == "open"]

        self._session_combo.clear()
        if not self._sessions:
            self._session_combo.setEnabled(False)
            self._submit_btn.setEnabled(False)
            self._no_sessions_lbl.setVisible(True)
            return

        self._no_sessions_lbl.setVisible(False)
        self._session_combo.setEnabled(True)
        self._submit_btn.setEnabled(True)

        for s in self._sessions:
            try:
                date_str = datetime.date.fromisoformat(s.get("date", "")).strftime("%d %b %Y")
            except Exception:
                date_str = s.get("date", "")
            label = f"{s.get('session_type', 'Session')}  —  {date_str}"
            self._session_combo.addItem(label)

    # ------------------------------------------------------------------ #
    #  Slots                                                               #
    # ------------------------------------------------------------------ #

    def _on_new_session(self):
        """Create a new session — requires admin access."""
        if not self._require_admin():
            return
        if not constants.REVIEW_TYPES:
            return
        dlg = _PickSessionTypeDialog(parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        session_type = dlg.selected_type
        if not session_type:
            return
        create_session(self._catalog_root, session_type)
        self._load_sessions()
        # Select the newly created session (it's newest, so index 0)
        self._session_combo.setCurrentIndex(0)

    def _require_admin(self) -> bool:
        """Return True if admin is already unlocked, or after PIN verification."""
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

    def _on_submit(self):
        if not self._sessions:
            return

        idx          = self._session_combo.currentIndex()
        session      = self._sessions[idx]
        session_path = session["path"]
        note         = self._note_field.toPlainText().strip()

        items = [
            {
                "file_path":       fp,
                "submitted_by":    constants.CURRENT_USER,
                "submission_note": note,
            }
            for fp in self._file_paths
        ]
        add_items(session_path, items)

        # Tight coupling: set each shot's .meta status to "Review"
        for fp in self._file_paths:
            try:
                p    = Path(fp)
                data = read_meta(p)
                if data.get("status") != "Approved":
                    data["status"] = "Review"
                    write_meta(p, data)
            except Exception:
                pass

        self.accept()


# ── Inline session-type picker ────────────────────────────────────────────── #

class _PickSessionTypeDialog(QDialog):
    """Small dialog to pick a session type when creating a new session."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Review Session")
        self.setFixedWidth(320)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setStyleSheet(f"background-color: {constants.BORDER};")
        self.selected_type = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(8)

        lbl = QLabel("Session Type")
        lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 11px; background: transparent;"
        )
        outer.addWidget(lbl)

        self._combo = QComboBox()
        self._combo.addItems(constants.REVIEW_TYPES)
        self._combo.setFixedHeight(34)
        self._combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {constants.BG};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px; padding: 2px 8px; font-size: 13px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {constants.BORDER};
                color: {constants.TEXT_PRI};
                selection-background-color: {constants.ACCENT};
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
        """)
        outer.addWidget(self._combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(30)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT};
                color: {constants.TEXT_SEC};
                border: none; border-radius: 4px; padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {constants.SPLITTER_COLOR};
                color: {constants.TEXT_PRI};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)

        create_btn = QPushButton("Create")
        create_btn.setFixedHeight(30)
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT_HI};
                color: white; border: none; border-radius: 4px;
                padding: 4px 16px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #1a95e8; }}
        """)
        create_btn.clicked.connect(self._on_create)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(create_btn)
        outer.addLayout(btn_row)

    def _on_create(self):
        self.selected_type = self._combo.currentText()
        self.accept()
