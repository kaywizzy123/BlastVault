"""
review_manager_dialog.py
────────────────────────
Browse and manage review sessions for a catalog root.

Features
--------
  • Session list with search bar + All / Open / Completed filter tabs
  • Create new session (by type or from a saved template)
  • Mark session complete / reopen / delete  (admin)
  • Manage session templates  (admin)  — save, delete
  • Opens the full review viewer for any session
"""
import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QLineEdit, QMessageBox,
    QComboBox, QAction,
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap

from core import constants
from core.reviews import (
    list_sessions, create_session, mark_completed,
    reopen_session, delete_session,
    list_templates, save_template, delete_template,
)
from dialogs.submit_review_dialog import _PickSessionTypeDialog


# ── Filter constants ──────────────────────────────────────────────────────── #
_FILTER_ALL       = "All"
_FILTER_OPEN      = "Open"
_FILTER_COMPLETED = "Completed"


class ReviewManagerDialog(QDialog):
    """Browse and manage review sessions for *catalog_root*."""

    # Forwarded from ReviewSessionDialog: (file_path, new_status)
    item_reviewed = pyqtSignal(str, str)

    def __init__(self, catalog_root: str, parent=None):
        super().__init__(parent)
        self._catalog_root  = catalog_root
        self._filter_status = _FILTER_ALL   # "All" | "Open" | "Completed"
        self._search_text   = ""

        self.setWindowTitle("Review Sessions")
        self.setMinimumWidth(680)
        self.setMinimumHeight(460)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint
        )
        self.setStyleSheet(f"background-color: {constants.BORDER};")

        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self._load_sessions()

    # ------------------------------------------------------------------ #
    #  UI scaffold                                                         #
    # ------------------------------------------------------------------ #

    def create_widgets(self):
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search sessions…")
        self._search_box.setFixedHeight(32)
        self._search_box.setStyleSheet(f"""
            QLineEdit {{
                background-color: {constants.BG};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 6px;
                padding: 4px 10px 4px 32px;
                font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {constants.ACCENT_HI}; }}
        """)
        _search_icon_action = QAction(
            QIcon(str(constants.ICONS_DIR / "search.png")), "", self._search_box
        )
        self._search_box.addAction(_search_icon_action, QLineEdit.LeadingPosition)

        self._filter_btns: dict[str, QPushButton] = {}
        for label in [_FILTER_ALL, _FILTER_OPEN, _FILTER_COMPLETED]:
            btn = QPushButton(label)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setChecked(label == _FILTER_ALL)
            self._filter_btns[label] = btn
        self._apply_filter_styles()

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )

        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch()
        self._scroll.setWidget(self._list_container)

        self._empty_lbl = QLabel("No sessions match your search.")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 12px; background: transparent;"
        )
        self._empty_lbl.setVisible(False)

        self._new_btn  = None
        self._tmpl_btn = None
        if constants.can_admin():
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

            self._tmpl_btn = QPushButton("☰ Templates")
            self._tmpl_btn.setFixedHeight(32)
            self._tmpl_btn.setCursor(Qt.PointingHandCursor)
            self._tmpl_btn.setToolTip("Create a session from a template, or manage templates")
            self._tmpl_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {constants.ACCENT};
                    color: {constants.TEXT_SEC};
                    border: 1px solid {constants.SPLITTER_COLOR};
                    border-radius: 4px; padding: 4px 12px;
                }}
                QPushButton:hover {{
                    background-color: {constants.SPLITTER_COLOR};
                    color: {constants.TEXT_PRI};
                }}
            """)

        self._close_btn = QPushButton("Close")
        self._close_btn.setFixedHeight(32)
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setStyleSheet(f"""
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

    def create_layout(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        icon_lbl = QLabel()
        pix = QPixmap(str(constants.ICONS_DIR / "dashboards.png"))
        if not pix.isNull():
            icon_lbl.setPixmap(
                pix.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        icon_lbl.setStyleSheet("background: transparent;")
        header_row.addWidget(icon_lbl)
        title_lbl = QLabel("Review Sessions")
        title_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: bold;"
            f"color: {constants.TEXT_PRI}; background: transparent;"
        )
        header_row.addWidget(title_lbl, stretch=1)
        outer.addLayout(header_row)

        sep0 = QFrame()
        sep0.setFrameShape(QFrame.HLine)
        sep0.setFixedHeight(1)
        sep0.setStyleSheet(f"background-color: {constants.SPLITTER_COLOR};")
        outer.addWidget(sep0)

        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)
        filter_bar.addWidget(self._search_box, stretch=1)
        for btn in self._filter_btns.values():
            filter_bar.addWidget(btn)
        outer.addLayout(filter_bar)

        outer.addWidget(self._scroll, stretch=1)
        outer.addWidget(self._empty_lbl, stretch=1)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        if self._new_btn is not None:
            toolbar.addWidget(self._new_btn)
        if self._tmpl_btn is not None:
            toolbar.addWidget(self._tmpl_btn)
        toolbar.addStretch()
        toolbar.addWidget(self._close_btn)
        outer.addLayout(toolbar)

    def create_connections(self):
        self._search_box.textChanged.connect(self._on_search_changed)
        for label, btn in self._filter_btns.items():
            btn.clicked.connect(lambda *_, _l=label: self._set_filter(_l))
        if self._new_btn is not None:
            self._new_btn.clicked.connect(self._on_new_session)
        if self._tmpl_btn is not None:
            self._tmpl_btn.clicked.connect(self._on_open_templates)
        self._close_btn.clicked.connect(self.accept)

    # ------------------------------------------------------------------ #
    #  Filter helpers                                                      #
    # ------------------------------------------------------------------ #

    def _apply_filter_styles(self):
        for label, btn in self._filter_btns.items():
            active = (label == self._filter_status)
            if active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {constants.ACCENT_HI};
                        color: white;
                        border: none; border-radius: 6px;
                        padding: 2px 12px; font-size: 12px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {constants.ACCENT};
                        color: {constants.TEXT_SEC};
                        border: 1px solid {constants.SPLITTER_COLOR};
                        border-radius: 6px; padding: 2px 12px; font-size: 12px;
                    }}
                    QPushButton:hover {{
                        background-color: {constants.SPLITTER_COLOR};
                        color: {constants.TEXT_PRI};
                    }}
                """)

    def _set_filter(self, label: str):
        self._filter_status = label
        for k, btn in self._filter_btns.items():
            btn.setChecked(k == label)
        self._apply_filter_styles()
        self._load_sessions()

    def _on_search_changed(self, text: str):
        self._search_text = text.strip().lower()
        self._load_sessions()

    # ------------------------------------------------------------------ #
    #  Session loading                                                     #
    # ------------------------------------------------------------------ #

    def _load_sessions(self):
        """Rebuild the session rows applying current search + filter."""
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_sessions = list_sessions(self._catalog_root)

        # Apply status filter
        if self._filter_status == _FILTER_OPEN:
            sessions = [s for s in all_sessions if s.get("status") == "open"]
        elif self._filter_status == _FILTER_COMPLETED:
            sessions = [s for s in all_sessions if s.get("status") == "completed"]
        else:
            sessions = all_sessions

        # Apply search text
        if self._search_text:
            q = self._search_text
            filtered = []
            for s in sessions:
                stype = s.get("session_type", "").lower()
                sdate = s.get("date", "").lower()
                sid   = s.get("id", "").lower()
                if q in stype or q in sdate or q in sid:
                    filtered.append(s)
            sessions = filtered

        if not sessions:
            self._scroll.setVisible(False)
            self._empty_lbl.setVisible(True)
            if not all_sessions:
                self._empty_lbl.setText(
                    'No sessions yet.  Create one with  "+ New Session".'
                )
            elif not self._search_text and self._filter_status == _FILTER_ALL:
                self._empty_lbl.setText("No sessions yet.  Create one below.")
            else:
                self._empty_lbl.setText("No sessions match your search.")
            return

        self._scroll.setVisible(True)
        self._empty_lbl.setVisible(False)

        for s in sessions:
            row = self._make_session_row(s)
            self._list_layout.insertWidget(self._list_layout.count() - 1, row)

    def _make_session_row(self, s: dict) -> QWidget:
        is_open    = s.get("status") == "open"
        item_count = len(s.get("items", []))
        reviewed   = sum(1 for it in s.get("items", []) if it.get("review_status"))
        pending    = item_count - reviewed
        urgent_n   = sum(
            1 for it in s.get("items", []) if it.get("priority") == "urgent"
        )

        try:
            date_str = datetime.date.fromisoformat(
                s.get("date", "")
            ).strftime("%d %b %Y")
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
                border: none; background: transparent;
            }}
        """)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(14, 10, 14, 10)
        rl.setSpacing(10)

        # Status dot
        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setAttribute(Qt.WA_StyledBackground, True)
        dot.setStyleSheet(
            f"background-color: "
            f"{'#4caf7d' if is_open else constants.TEXT_SEC}; border-radius: 5px;"
        )
        rl.addWidget(dot)

        # Name + metadata column
        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        name_lbl = QLabel(s.get("session_type", "Session"))
        name_lbl.setStyleSheet(
            f"color: {constants.TEXT_PRI}; font-size: 13px; font-weight: bold;"
        )
        name_lbl.setMaximumWidth(260)
        info_col.addWidget(name_lbl)

        meta_parts = [
            date_str,
            f"{item_count} shot{'s' if item_count != 1 else ''}",
            f"{reviewed}/{item_count} reviewed",
        ]
        if urgent_n:
            meta_parts.append(f"⚡ {urgent_n} urgent")
        if pending and is_open:
            meta_parts.append(f"{pending} pending")

        meta_lbl = QLabel("   ·   ".join(meta_parts))
        meta_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 11px;"
        )
        info_col.addWidget(meta_lbl)
        rl.addLayout(info_col, stretch=1)

        # Status chip
        status_chip = QLabel("Open" if is_open else "Completed")
        chip_bg  = "#4caf7d" if is_open else constants.ACCENT
        chip_col = "white" if is_open else constants.TEXT_SEC
        status_chip.setStyleSheet(f"""
            background-color: {chip_bg}; color: {chip_col};
            border-radius: 8px; padding: 2px 10px;
            font-size: 11px; font-weight: bold;
        """)
        status_chip.setAttribute(Qt.WA_StyledBackground, True)
        rl.addWidget(status_chip)

        # Open button — arrow icon
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
            QPushButton:hover {{ background-color: {constants.ACCENT_HI}; }}
        """)
        open_btn.clicked.connect(lambda *_, _s=s: self._open_session(_s))
        rl.addWidget(open_btn)

        if constants.can_admin():
            # Complete / Reopen
            if is_open:
                done_btn = QPushButton("Complete")
                done_btn.setIcon(QIcon(str(constants.ICONS_DIR / "check.png")))
                done_btn.setIconSize(QSize(13, 13))
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

            # Save as template
            tmpl_btn = QPushButton()
            tmpl_btn.setIcon(QIcon(str(constants.ICONS_DIR / "bookmark.png")))
            tmpl_btn.setIconSize(QSize(13, 13))
            tmpl_btn.setFixedSize(30, 28)
            tmpl_btn.setCursor(Qt.PointingHandCursor)
            tmpl_btn.setToolTip("Save as template")
            tmpl_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {constants.ACCENT};
                    border: none; border-radius: 4px;
                }}
                QPushButton:hover {{ background-color: #e5a820; }}
            """)
            tmpl_btn.clicked.connect(
                lambda *_, _s=s: self._on_save_as_template(_s)
            )
            rl.addWidget(tmpl_btn)

            # Delete
            del_btn = QPushButton()
            del_btn.setIcon(QIcon(str(constants.ICONS_DIR / "bin.png")))
            del_btn.setIconSize(QSize(14, 14))
            del_btn.setFixedSize(30, 28)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setToolTip("Delete session")
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {constants.ACCENT};
                    border: none; border-radius: 4px;
                }}
                QPushButton:hover {{ background-color: {constants.FAIL}; }}
            """)
            del_btn.clicked.connect(
                lambda *_, _sp=s["path"], _st=s.get("session_type", "Session"):
                    self._on_delete_session(_sp, _st)
            )
            rl.addWidget(del_btn)

        return row

    # ------------------------------------------------------------------ #
    #  Slots — sessions                                                    #
    # ------------------------------------------------------------------ #

    def _open_session(self, s: dict):
        from dialogs.review_session_dialog import ReviewSessionDialog
        dlg = ReviewSessionDialog(s["path"], parent=self)
        dlg.item_reviewed.connect(self.item_reviewed)
        dlg.exec_()
        self._load_sessions()

    def _on_new_session(self):
        if not self._require_admin():
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

    def _on_delete_session(self, session_path: str, session_type: str):
        if not self._require_admin():
            return
        reply = QMessageBox.warning(
            self,
            "Delete Session",
            f'Permanently delete  "{session_type}"?\n\nThis cannot be undone.',
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if reply != QMessageBox.Yes:
            return
        delete_session(session_path)
        self._load_sessions()

    def _on_save_as_template(self, session: dict):
        """Save the given session's type as a reusable template."""
        if not self._require_admin():
            return
        dlg = _SaveTemplateDialog(session, self._catalog_root, parent=self)
        dlg.exec_()
        # No need to reload sessions — templates live in a separate file

    # ------------------------------------------------------------------ #
    #  Slots — templates                                                   #
    # ------------------------------------------------------------------ #

    def _on_open_templates(self):
        """Open the template manager dialog."""
        if not self._require_admin():
            return
        dlg = TemplateManagerDialog(self._catalog_root, parent=self)
        dlg.session_created.connect(self._load_sessions)
        dlg.exec_()

    # ------------------------------------------------------------------ #
    #  Admin gate                                                          #
    # ------------------------------------------------------------------ #

    def _require_admin(self) -> bool:
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


# ═══════════════════════════════════════════════════════════════════════════ #
#  Save-as-template dialog                                                    #
# ═══════════════════════════════════════════════════════════════════════════ #

class _SaveTemplateDialog(QDialog):
    """Quick dialog to name and save a session as a template."""

    def __init__(self, session: dict, catalog_root: str, parent=None):
        super().__init__(parent)
        self._session      = session
        self._catalog_root = catalog_root

        self.setWindowTitle("Save as Template")
        self.setMinimumWidth(380)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {constants.BORDER};")
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        _field_style = f"""
            QLineEdit {{
                background-color: {constants.BG};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px; padding: 4px 10px; font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {constants.ACCENT_HI}; }}
        """
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. End of Day Dailies")
        self._name_edit.setText(self._session.get("session_type", ""))
        self._name_edit.setFixedHeight(32)
        self._name_edit.setStyleSheet(_field_style)

        self._note_edit = QLineEdit()
        self._note_edit.setPlaceholderText("Brief description of this template")
        self._note_edit.setFixedHeight(32)
        self._note_edit.setStyleSheet(_field_style)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedHeight(30)
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.setStyleSheet(f"""
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

        self._save_btn = QPushButton("Save Template")
        self._save_btn.setFixedHeight(30)
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT_HI};
                color: white; border: none; border-radius: 4px;
                padding: 2px 14px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #1a95e8; }}
        """)

    def create_layout(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(22, 20, 22, 20)
        vl.setSpacing(12)

        title = QLabel("Save Session as Template")
        title.setStyleSheet(
            f"color: {constants.TEXT_PRI}; font-size: 14px; font-weight: bold;"
            f"background: transparent;"
        )
        vl.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {constants.SPLITTER_COLOR};")
        vl.addWidget(sep)

        name_lbl = QLabel("Template name:")
        name_lbl.setStyleSheet(
            f"color: {constants.TEXT_PRI}; font-size: 12px; background: transparent;"
        )
        vl.addWidget(name_lbl)
        vl.addWidget(self._name_edit)

        note_lbl = QLabel("Note <i>(optional)</i>:")
        note_lbl.setStyleSheet(
            f"color: {constants.TEXT_PRI}; font-size: 12px; background: transparent;"
        )
        vl.addWidget(note_lbl)
        vl.addWidget(self._note_edit)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._save_btn)
        vl.addLayout(btn_row)

    def create_connections(self):
        self._cancel_btn.clicked.connect(self.reject)
        self._save_btn.clicked.connect(self._on_save)

    def _on_save(self):
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Name Required", "Please enter a template name.")
            return
        template = {
            "name":  name,
            "type":  self._session.get("session_type", name),
            "note":  self._note_edit.text().strip(),
        }
        save_template(self._catalog_root, template)
        QMessageBox.information(
            self, "Saved",
            f'Template "{name}" saved.\nUse "☰ Templates" to create sessions from it.'
        )
        self.accept()


# ═══════════════════════════════════════════════════════════════════════════ #
#  Template manager dialog                                                    #
# ═══════════════════════════════════════════════════════════════════════════ #

class TemplateManagerDialog(QDialog):
    """View saved session templates, create sessions from them, or delete them."""

    # Emitted when a session is created from a template
    session_created = pyqtSignal()

    def __init__(self, catalog_root: str, parent=None):
        super().__init__(parent)
        self._catalog_root = catalog_root

        self.setWindowTitle("Session Templates")
        self.setMinimumWidth(520)
        self.setMinimumHeight(380)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint
        )
        self.setStyleSheet(f"background-color: {constants.BORDER};")
        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self._load_templates()

    # ------------------------------------------------------------------ #

    def create_widgets(self):
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )

        self._tmpl_container = QWidget()
        self._tmpl_container.setStyleSheet("background: transparent;")
        self._tmpl_layout = QVBoxLayout(self._tmpl_container)
        self._tmpl_layout.setContentsMargins(0, 0, 0, 0)
        self._tmpl_layout.setSpacing(6)
        self._tmpl_layout.addStretch()
        self._scroll.setWidget(self._tmpl_container)

        self._empty_lbl = QLabel(
            "No templates saved yet.\n"
            "Use the  ★  button on any session to save it as a template."
        )
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 12px; background: transparent;"
        )
        self._empty_lbl.setVisible(False)

        self._close_btn = QPushButton("Close")
        self._close_btn.setFixedHeight(32)
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setStyleSheet(f"""
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

    def create_layout(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 20)
        outer.setSpacing(10)

        title_row = QHBoxLayout()
        title_lbl = QLabel("Session Templates")
        title_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: bold;"
            f"color: {constants.TEXT_PRI}; background: transparent;"
        )
        title_row.addWidget(title_lbl, stretch=1)
        outer.addLayout(title_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {constants.SPLITTER_COLOR};")
        outer.addWidget(sep)

        hint = QLabel("Save any session as a template using the  ★  button in the session list.")
        hint.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 11px; background: transparent;"
        )
        outer.addWidget(hint)

        outer.addWidget(self._scroll, stretch=1)
        outer.addWidget(self._empty_lbl, stretch=1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        footer.addStretch()
        footer.addWidget(self._close_btn)
        outer.addLayout(footer)

    def create_connections(self):
        self._close_btn.clicked.connect(self.accept)

    def _load_templates(self):
        while self._tmpl_layout.count() > 1:
            item = self._tmpl_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        templates = list_templates(self._catalog_root)
        if not templates:
            self._scroll.setVisible(False)
            self._empty_lbl.setVisible(True)
            return

        self._scroll.setVisible(True)
        self._empty_lbl.setVisible(False)

        for tmpl in templates:
            row = self._make_template_row(tmpl)
            self._tmpl_layout.insertWidget(self._tmpl_layout.count() - 1, row)

    def _make_template_row(self, tmpl: dict) -> QWidget:
        name  = tmpl.get("name", "Unnamed")
        ttype = tmpl.get("type", name)
        note  = tmpl.get("note", "")

        row = QFrame()
        row.setObjectName("tmplRow")
        row.setFrameShape(QFrame.StyledPanel)
        row.setStyleSheet(f"""
            QFrame#tmplRow {{
                background-color: {constants.BG};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 6px;
            }}
            QFrame#tmplRow QLabel {{ border: none; background: transparent; }}
        """)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(14, 10, 14, 10)
        rl.setSpacing(10)

        # Star icon
        star = QLabel("★")
        star.setStyleSheet("color: #e5a820; font-size: 14px; background: transparent;")
        star.setFixedWidth(18)
        rl.addWidget(star)

        # Name + type + note
        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            f"color: {constants.TEXT_PRI}; font-size: 13px; font-weight: bold;"
        )
        info.addWidget(name_lbl)

        meta_parts = [f"Type: {ttype}"]
        if note:
            meta_parts.append(note)
        meta_lbl = QLabel("  ·  ".join(meta_parts))
        meta_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 11px;"
        )
        meta_lbl.setWordWrap(True)
        info.addWidget(meta_lbl)
        rl.addLayout(info, stretch=1)

        # "Use" button — creates a new session from this template
        use_btn = QPushButton("Use")
        use_btn.setFixedHeight(28)
        use_btn.setCursor(Qt.PointingHandCursor)
        use_btn.setToolTip(f'Create a new session of type "{ttype}"')
        use_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT_HI};
                color: white; border: none;
                border-radius: 4px; padding: 2px 12px; font-size: 12px;
            }}
            QPushButton:hover {{ background-color: #1a95e8; }}
        """)
        use_btn.clicked.connect(lambda *_, _t=tmpl: self._on_use_template(_t))
        rl.addWidget(use_btn)

        # Delete button
        del_btn = QPushButton()
        del_btn.setIcon(QIcon(str(constants.ICONS_DIR / "bin.png")))
        del_btn.setIconSize(QSize(13, 13))
        del_btn.setFixedSize(28, 28)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setToolTip("Delete template")
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT};
                border: none; border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {constants.FAIL}; }}
        """)
        del_btn.clicked.connect(lambda *_, _n=name: self._on_delete_template(_n))
        rl.addWidget(del_btn)

        return row

    # ------------------------------------------------------------------ #

    def _on_use_template(self, tmpl: dict):
        session_type = tmpl.get("type", tmpl.get("name", "Review"))
        create_session(self._catalog_root, session_type)
        self.session_created.emit()
        QMessageBox.information(
            self,
            "Session Created",
            f'New "{session_type}" session created.\n'
            f"You can find it in the session list.",
        )

    def _on_delete_template(self, name: str):
        reply = QMessageBox.warning(
            self,
            "Delete Template",
            f'Delete template "{name}"?\n\nThis cannot be undone.',
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if reply != QMessageBox.Yes:
            return
        delete_template(self._catalog_root, name)
        self._load_templates()
