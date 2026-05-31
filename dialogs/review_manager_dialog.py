"""
review_manager_dialog.py
────────────────────────
Shows all review sessions for a catalog root, lets admins create new ones,
and opens the full review viewer for any session.

Usage
-----
    dlg = ReviewManagerDialog(catalog_root, parent=self)
    dlg.exec_()
"""
import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame,
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon

from core import constants
from core.reviews import list_sessions, create_session, mark_completed, reopen_session
from dialogs.submit_review_dialog import _PickSessionTypeDialog


class ReviewManagerDialog(QDialog):
    """Browse and manage review sessions for *catalog_root*."""

    # Forwarded from ReviewSessionDialog: (file_path, new_status)
    item_reviewed = pyqtSignal(str, str)

    def __init__(self, catalog_root: str, parent=None):
        super().__init__(parent)
        self._catalog_root = catalog_root

        self.setWindowTitle("Review Sessions")
        self.setMinimumWidth(580)
        self.setMinimumHeight(420)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint)
        self.setStyleSheet(f"background-color: {constants.BORDER};")

        self._build_ui()
        self._load_sessions()

    # ------------------------------------------------------------------ #
    #  UI                                                                  #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        # ── Icon + title ──────────────────────────────────────────────────
        icon_lbl = QLabel()
        pix = QPixmap(str(constants.ICONS_DIR / "dashboards.png"))
        if not pix.isNull():
            icon_lbl.setPixmap(
                pix.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent;")
        outer.addWidget(icon_lbl)

        title_lbl = QLabel("Review Sessions")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(
            f"font-size: 15px; font-weight: bold;"
            f"color: {constants.TEXT_PRI}; background: transparent;"
        )
        outer.addWidget(title_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {constants.SPLITTER_COLOR};")
        outer.addWidget(sep)

        # ── Session list (scroll area) ────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
        """)

        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._list_container)
        outer.addWidget(self._scroll, stretch=1)

        # ── Empty-state label ─────────────────────────────────────────────
        self._empty_lbl = QLabel("No sessions yet.  Create one below.")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 12px; background: transparent;"
        )
        self._empty_lbl.setVisible(False)
        outer.addWidget(self._empty_lbl)

        # ── Bottom toolbar ────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._new_btn = QPushButton("+ New Session")
        self._new_btn.setFixedHeight(32)
        self._new_btn.setCursor(Qt.PointingHandCursor)
        self._new_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT_HI};
                color: white; border: none; border-radius: 4px;
                padding: 4px 14px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #1a95e8; }}
        """)
        self._new_btn.clicked.connect(self._on_new_session)
        toolbar.addWidget(self._new_btn)

        toolbar.addStretch()

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
        toolbar.addWidget(close_btn)

        outer.addLayout(toolbar)

    # ------------------------------------------------------------------ #
    #  Session loading                                                     #
    # ------------------------------------------------------------------ #

    def _load_sessions(self):
        """Rebuild the session rows from disk."""
        # Clear existing rows (except final stretch)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sessions = list_sessions(self._catalog_root)
        if not sessions:
            self._scroll.setVisible(False)
            self._empty_lbl.setVisible(True)
            return

        self._scroll.setVisible(True)
        self._empty_lbl.setVisible(False)

        for s in sessions:
            row = self._make_session_row(s)
            self._list_layout.insertWidget(self._list_layout.count() - 1, row)

    def _make_session_row(self, s: dict) -> QWidget:
        """Build a single session row widget."""
        is_open = s.get("status") == "open"
        item_count = len(s.get("items", []))
        reviewed = sum(
            1 for it in s.get("items", []) if it.get("review_status")
        )

        try:
            date_str = datetime.date.fromisoformat(s.get("date", "")).strftime("%d %b %Y")
        except Exception:
            date_str = s.get("date", "")

        row = QFrame()
        row.setObjectName("sessionRow")
        row.setFrameShape(QFrame.StyledPanel)
        row.setStyleSheet(f"""
            QFrame#sessionRow {{
                background-color: {constants.BG};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 6px;
            }}
            QFrame#sessionRow QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(14, 10, 14, 10)
        rl.setSpacing(12)

        # Status dot
        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setAttribute(Qt.WA_StyledBackground, True)
        dot_color = constants.SUCCESS if is_open else constants.TEXT_SEC
        dot.setStyleSheet(
            f"background-color: {dot_color}; border-radius: 5px;"
        )
        rl.addWidget(dot)

        # Session name + date
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        name_lbl = QLabel(s.get("session_type", "Session"))
        name_lbl.setStyleSheet(
            f"color: {constants.TEXT_PRI}; font-size: 13px; font-weight: bold;"
            f"background: transparent;"
        )
        info_col.addWidget(name_lbl)

        meta_lbl = QLabel(f"{date_str}   ·   {item_count} shot{'s' if item_count != 1 else ''}   ·   {reviewed} reviewed")
        meta_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 11px; background: transparent;"
        )
        info_col.addWidget(meta_lbl)
        rl.addLayout(info_col, stretch=1)

        # Status chip
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
        rl.addWidget(status_chip)

        # Open button — icon-only arrow
        open_btn = QPushButton()
        open_btn.setIcon(QIcon(str(constants.ICONS_DIR / "right-arrow.png")))
        open_btn.setIconSize(QSize(14, 14))
        open_btn.setFixedSize(30, 28)
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setToolTip("Open session")
        open_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT};
                border: none; border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {constants.ACCENT_HI};
            }}
        """)
        # Capture session dict by value
        open_btn.clicked.connect(lambda *_, _s=s: self._open_session(_s))
        rl.addWidget(open_btn)

        # Action button: "Complete" for open sessions, "Reopen" for completed ones
        if is_open:
            done_btn = QPushButton("Complete")
            done_btn.setIcon(QIcon(str(constants.ICONS_DIR / "check.png")))
            done_btn.setIconSize(QSize(14, 14))
            done_btn.setFixedHeight(28)
            done_btn.setCursor(Qt.PointingHandCursor)
            done_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {constants.ACCENT};
                    color: {constants.TEXT_SEC};
                    border: 1px solid {constants.SPLITTER_COLOR};
                    border-radius: 4px; padding: 2px 10px; font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {constants.SUCCESS};
                    color: white; border-color: {constants.SUCCESS};
                }}
            """)
            done_btn.clicked.connect(
                lambda *_, _sp=s["path"]: self._on_mark_complete(_sp)
            )
            rl.addWidget(done_btn)
        else:
            reopen_btn = QPushButton("Reopen")
            reopen_btn.setFixedHeight(28)
            reopen_btn.setCursor(Qt.PointingHandCursor)
            reopen_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {constants.ACCENT};
                    color: {constants.TEXT_SEC};
                    border: 1px solid {constants.SPLITTER_COLOR};
                    border-radius: 4px; padding: 2px 10px; font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {constants.ACCENT_HI};
                    color: white; border-color: {constants.ACCENT_HI};
                }}
            """)
            reopen_btn.clicked.connect(
                lambda *_, _sp=s["path"]: self._on_reopen_session(_sp)
            )
            rl.addWidget(reopen_btn)

        return row

    # ------------------------------------------------------------------ #
    #  Slots                                                               #
    # ------------------------------------------------------------------ #

    def _open_session(self, s: dict):
        """Open the review session dialog for *s*."""
        from dialogs.review_session_dialog import ReviewSessionDialog
        dlg = ReviewSessionDialog(s["path"], parent=self)
        dlg.item_reviewed.connect(self.item_reviewed)   # bubble up to main window
        dlg.exec_()
        # Reload in case reviews were submitted from within
        self._load_sessions()

    def _on_new_session(self):
        if not self._require_admin():
            return
        if not constants.REVIEW_TYPES:
            return
        dlg = _PickSessionTypeDialog(parent=self)
        if dlg.exec_() != QDialog.Accepted or not dlg.selected_type:
            return
        create_session(self._catalog_root, dlg.selected_type)
        self._load_sessions()

    def _on_mark_complete(self, session_path: str):
        if not self._require_admin():
            return
        mark_completed(session_path)
        self._load_sessions()

    def _on_reopen_session(self, session_path: str):
        if not self._require_admin():
            return
        reopen_session(session_path)
        self._load_sessions()

    # ------------------------------------------------------------------ #
    #  Admin gate                                                          #
    # ------------------------------------------------------------------ #

    def _require_admin(self) -> bool:
        """Return True if admin is already unlocked, or after successful PIN entry.

        Handles both the first-time PIN setup and subsequent verifications so
        admin actions can be triggered from within this dialog without needing
        to use the header padlock first.
        """
        if not constants.STATUS_LOCKED:
            return True

        import hashlib
        from dialogs.pin_dialog import PinInputDialog, PinSetupDialog

        if not constants.ADMIN_PIN_HASH:
            # No PIN set yet — offer setup
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

        # Unlock for this session
        constants.STATUS_LOCKED = False
        return True
