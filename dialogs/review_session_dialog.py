"""
review_session_dialog.py
────────────────────────
Full review viewer for a single session.

Features
--------
  • Shot cards with priority indicator, version badge, play button
  • Approve / Revision / On Hold per shot (reviewer + admin)
  • Frame range annotation in the reviewer note dialog
  • Batch approve / reject — checkbox mode + batch action bar
  • Version history viewer — see all previous submissions per shot
  • Compare button — opens side-by-side viewer for current vs previous version
"""
import datetime
import subprocess
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QTextEdit, QSizePolicy,
    QCheckBox, QSpinBox, QAction,
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon

from core import constants
from core.reviews import (
    read_session, write_session,
    set_item_review, batch_set_review,
    set_item_priority, mark_completed,
)
from core.meta import read_meta, write_meta
from core.notes import add_note


# ── Colour maps ───────────────────────────────────────────────────────────── #
_REVIEW_STATUS_COLORS = {
    "Approved":  constants.SUCCESS,
    "Revision":  "#e5a820",
    "On Hold":   constants.FAIL,
    "":          constants.TEXT_SEC,
}
_PRIORITY_COLORS = {
    "urgent": ("#ff4444", "⚡"),
    "high":   ("#e5a820", "↑"),
    "normal": (None,      ""),
}


class ReviewSessionDialog(QDialog):
    """Full review viewer for the session at *session_path*."""

    item_reviewed = pyqtSignal(str, str)   # (file_path, new_status)

    def __init__(self, session_path: str, parent=None):
        super().__init__(parent)
        self._session_path  = session_path
        self._batch_mode    = False
        self._checked_ids: set[str] = set()

        self.setWindowTitle("Review Session")
        self.setMinimumWidth(720)
        self.setMinimumHeight(520)
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

        # Header (filled in _load_session) — fixed height, never scrolls away
        self._header_widget = QWidget()
        self._header_widget.setStyleSheet("background: transparent;")
        self._header_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self._header_layout = QVBoxLayout(self._header_widget)
        self._header_layout.setContentsMargins(0, 0, 0, 0)
        self._header_layout.setSpacing(4)
        self._outer.addWidget(self._header_widget)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {constants.SPLITTER_COLOR};")
        self._outer.addWidget(sep)

        # ── Batch toolbar (hidden until batch mode is on) ─────────────────
        self._batch_bar = QWidget()
        self._batch_bar.setStyleSheet(
            f"background-color: {constants.BG}; border-radius: 4px;"
        )
        self._batch_bar.setVisible(False)
        bb = QHBoxLayout(self._batch_bar)
        bb.setContentsMargins(10, 6, 10, 6)
        bb.setSpacing(8)

        self._sel_lbl = QLabel("0 selected")
        self._sel_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 11px; background: transparent;"
        )
        bb.addWidget(self._sel_lbl)
        bb.addStretch()

        for label, color, rs in [
            ("Approve All",  constants.SUCCESS, "Approved"),
            ("Revision All", "#e5a820",         "Revision"),
            ("Hold All",     constants.FAIL,    "On Hold"),
        ]:
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {constants.ACCENT};
                    color: {constants.TEXT_SEC};
                    border: 1px solid {constants.SPLITTER_COLOR};
                    border-radius: 4px; padding: 2px 10px; font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {color}; color: white;
                    border-color: {color};
                }}
            """)
            btn.clicked.connect(lambda *_, _rs=rs: self._on_batch_review(_rs))
            bb.addWidget(btn)

        self._outer.addWidget(self._batch_bar)

        # Shot card list
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

        # Empty state
        self._empty_lbl = QLabel("No shots in this session yet.")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 12px; background: transparent;"
        )
        self._empty_lbl.setVisible(False)
        self._outer.addWidget(self._empty_lbl, stretch=1)

        # Footer
        self._footer_layout = QHBoxLayout()
        self._footer_layout.setSpacing(8)
        self._outer.addLayout(self._footer_layout)

    # ------------------------------------------------------------------ #
    #  Session loading                                                     #
    # ------------------------------------------------------------------ #

    def _load_session(self):
        data = read_session(self._session_path)
        if not data:
            self._empty_lbl.setVisible(True)
            self._scroll.setVisible(False)
            return

        is_open    = data.get("status") == "open"
        items      = data.get("items", [])
        item_count = len(items)
        reviewed   = sum(1 for it in items if it.get("review_status"))
        pending    = item_count - reviewed
        urgent_n   = sum(1 for it in items if it.get("priority") == "urgent")

        # ── Header ────────────────────────────────────────────────────────
        _clear_layout(self._header_layout)

        try:
            date_str = datetime.date.fromisoformat(data.get("date", "")).strftime("%d %B %Y")
        except Exception:
            date_str = data.get("date", "")

        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        icon_lbl = QLabel()
        pix = QPixmap(str(constants.ICONS_DIR / "dashboards.png"))
        if not pix.isNull():
            icon_lbl.setPixmap(pix.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_lbl.setStyleSheet("background: transparent;")
        title_row.addWidget(icon_lbl)

        title_lbl = QLabel(data.get("session_type", "Review Session"))
        title_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: bold;"
            f"color: {constants.TEXT_PRI}; background: transparent;"
        )
        title_row.addWidget(title_lbl, stretch=1)

        # Batch select toggle
        if is_open and constants.can_review() and item_count > 0:
            self._batch_toggle_btn = QPushButton(
                "✕ Exit Select" if self._batch_mode else "☐ Select"
            )
            self._batch_toggle_btn.setFixedHeight(26)
            self._batch_toggle_btn.setCursor(Qt.PointingHandCursor)
            self._batch_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {constants.ACCENT};
                    color: {constants.TEXT_SEC};
                    border: 1px solid {constants.SPLITTER_COLOR};
                    border-radius: 4px; padding: 2px 10px; font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {constants.ACCENT_HI}; color: white;
                }}
            """)
            self._batch_toggle_btn.clicked.connect(self._toggle_batch_mode)
            title_row.addWidget(self._batch_toggle_btn)

        status_chip = QLabel("Open" if is_open else "Completed")
        chip_bg  = constants.SUCCESS if is_open else constants.ACCENT
        chip_col = "white" if is_open else constants.TEXT_SEC
        status_chip.setStyleSheet(f"""
            background-color: {chip_bg}; color: {chip_col};
            border-radius: 8px; padding: 2px 10px;
            font-size: 11px; font-weight: bold;
        """)
        status_chip.setAttribute(Qt.WA_StyledBackground, True)
        title_row.addWidget(status_chip)
        self._header_layout.addLayout(title_row)

        meta_parts = [date_str, f"{item_count} shot{'s' if item_count != 1 else ''}",
                      f"{reviewed}/{item_count} reviewed"]
        if is_open:
            if urgent_n:
                meta_parts.append(f"⚡ {urgent_n} urgent")
            if pending:
                meta_parts.append(f"{pending} pending")
        subtitle_lbl = QLabel("   ·   ".join(meta_parts))
        subtitle_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; font-size: 11px; background: transparent;"
        )
        self._header_layout.addWidget(subtitle_lbl)

        # ── Cards ─────────────────────────────────────────────────────────
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
                self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

        # ── Batch bar ─────────────────────────────────────────────────────
        self._batch_bar.setVisible(self._batch_mode)
        self._update_sel_label()

        # ── Footer ────────────────────────────────────────────────────────
        _clear_layout(self._footer_layout)

        if is_open and constants.can_admin():
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
        file_path       = item.get("file_path", "")
        submitted_by    = item.get("submitted_by", "")
        sub_note        = item.get("submission_note", "")
        review_status   = item.get("review_status", "")
        reviewer_note   = item.get("reviewer_note", "")
        frame_annots    = item.get("frame_annotations", [])
        item_id         = item.get("id", "")
        version         = item.get("version", 1)
        priority        = item.get("priority", "normal")
        version_history = item.get("version_history", [])

        pri_color, pri_icon = _PRIORITY_COLORS.get(priority, (None, ""))

        card = QFrame()
        card.setObjectName("shotCard")
        card.setFrameShape(QFrame.StyledPanel)
        border_color = pri_color or constants.SPLITTER_COLOR
        card.setStyleSheet(f"""
            QFrame#shotCard {{
                background-color: {constants.BG};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
            QFrame#shotCard QLabel {{ border: none; background: transparent; }}
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(6)

        # ── Top row ───────────────────────────────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Batch checkbox
        if self._batch_mode:
            _check_icon = str(constants.ICONS_DIR / "check.png").replace("\\", "/")
            cb = QCheckBox()
            cb.setChecked(item_id in self._checked_ids)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    background: transparent;
                    spacing: 0px;
                }}
                QCheckBox::indicator {{
                    width: 18px; height: 18px;
                    border: 2px solid {constants.SPLITTER_COLOR};
                    border-radius: 4px;
                    background-color: {constants.ACCENT};
                }}
                QCheckBox::indicator:hover {{
                    border-color: {constants.ACCENT_HI};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {constants.ACCENT_HI};
                    border-color: {constants.ACCENT_HI};
                    image: url("{_check_icon}");
                }}
            """)
            cb.toggled.connect(lambda checked, _id=item_id: self._on_check(checked, _id))
            top_row.addWidget(cb)

        # Priority icon
        if pri_icon:
            pri_lbl = QLabel(pri_icon)
            pri_lbl.setStyleSheet(
                f"color: {pri_color}; font-size: 14px; font-weight: bold;"
                f"background: transparent;"
            )
            pri_lbl.setToolTip(f"Priority: {priority.capitalize()}")
            top_row.addWidget(pri_lbl)

        # File name
        fname = file_path.replace("\\", "/").split("/")[-1] if file_path else "(unknown)"
        name_lbl = QLabel(fname)
        name_lbl.setStyleSheet(
            f"color: {constants.TEXT_PRI}; font-size: 13px; font-weight: bold;"
            f"background: transparent;"
        )
        name_lbl.setToolTip(file_path)
        top_row.addWidget(name_lbl, stretch=1)

        # Version badge
        if version > 1:
            ver_lbl = QLabel(f"v{version}")
            ver_lbl.setStyleSheet(f"""
                background-color: {constants.ACCENT_HI}33;
                color: {constants.ACCENT_HI};
                border-radius: 6px; padding: 1px 8px;
                font-size: 11px; font-weight: bold;
            """)
            ver_lbl.setAttribute(Qt.WA_StyledBackground, True)
            top_row.addWidget(ver_lbl)

        # Review status chip
        rs_color = _REVIEW_STATUS_COLORS.get(review_status, constants.TEXT_SEC)
        rs_lbl = QLabel(review_status if review_status else "Pending")
        rs_lbl.setStyleSheet(f"""
            background-color: {constants.SPLITTER_COLOR if not review_status else rs_color + '33'};
            color: {rs_color}; border-radius: 8px; padding: 1px 10px;
            font-size: 11px; font-weight: bold;
        """)
        rs_lbl.setAttribute(Qt.WA_StyledBackground, True)
        top_row.addWidget(rs_lbl)

        # Compare button (if there's a previous version)
        if version_history:
            cmp_btn = QPushButton("Compare")
            cmp_btn.setFixedHeight(26)
            cmp_btn.setCursor(Qt.PointingHandCursor)
            cmp_btn.setToolTip(f"Compare v{version} with v{version_history[-1]['version']}")
            cmp_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {constants.ACCENT};
                    color: {constants.TEXT_SEC};
                    border: 1px solid {constants.SPLITTER_COLOR};
                    border-radius: 4px; padding: 1px 8px; font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {constants.ACCENT_HI}; color: white;
                }}
            """)
            prev_fp = version_history[-1].get("file_path", file_path)
            cmp_btn.clicked.connect(
                lambda *_, a=file_path, b=prev_fp, va=version,
                vb=version_history[-1].get("version", 1):
                    self._open_compare(a, b, va, vb)
            )
            top_row.addWidget(cmp_btn)

        # History button
        if version_history:
            hist_btn = QPushButton(f"History ({len(version_history)})")
            hist_btn.setFixedHeight(26)
            hist_btn.setCursor(Qt.PointingHandCursor)
            hist_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {constants.ACCENT};
                    color: {constants.TEXT_SEC};
                    border: 1px solid {constants.SPLITTER_COLOR};
                    border-radius: 4px; padding: 1px 8px; font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {constants.SPLITTER_COLOR};
                    color: {constants.TEXT_PRI};
                }}
            """)
            hist_btn.clicked.connect(
                lambda *_, _h=version_history, _v=version: self._show_history(_h, _v)
            )
            top_row.addWidget(hist_btn)

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

        # ── Submitter / note ──────────────────────────────────────────────
        sub_parts = []
        if submitted_by:
            sub_parts.append(f"by {submitted_by}")
        sub_text = "  ·  ".join(sub_parts)
        display = f"{sub_text}  —  {sub_note}" if sub_text and sub_note else (sub_text or sub_note)
        if display:
            note_lbl = QLabel(display)
            note_lbl.setStyleSheet(
                f"color: {constants.TEXT_SEC}; font-size: 11px; background: transparent;"
            )
            note_lbl.setWordWrap(True)
            cl.addWidget(note_lbl)

        # ── Reviewer note ─────────────────────────────────────────────────
        if reviewer_note:
            rev_lbl = QLabel(f"📝  {reviewer_note}")
            rev_lbl.setStyleSheet(
                f"color: {constants.TEXT_SEC}; font-size: 11px;"
                f"font-style: italic; background: transparent;"
            )
            rev_lbl.setWordWrap(True)
            cl.addWidget(rev_lbl)

        # ── Frame annotations ─────────────────────────────────────────────
        for ann in frame_annots:
            start = ann.get("start", "")
            end   = ann.get("end", "")
            note  = ann.get("note", "")
            range_str = f"[{start}–{end}]" if start != "" and end != "" else ""
            ann_lbl = QLabel(f"🎞  {range_str}  {note}".strip())
            ann_lbl.setStyleSheet(
                f"color: {constants.ACCENT_HI}; font-size: 11px;"
                f"background: transparent;"
            )
            ann_lbl.setWordWrap(True)
            cl.addWidget(ann_lbl)

        # ── Review action buttons ─────────────────────────────────────────
        if session_open and not self._batch_mode:
            btn_row = QHBoxLayout()
            btn_row.setSpacing(6)

            # Priority switcher (admin only)
            if constants.can_admin():
                pri_label_map = {"normal": "Normal", "high": "High", "urgent": "Urgent ⚡"}
                from PyQt5.QtWidgets import QComboBox
                pri_combo = QComboBox()
                pri_combo.addItems(["Normal", "High", "Urgent ⚡"])
                pri_combo.setCurrentText(pri_label_map.get(priority, "Normal"))
                pri_combo.setFixedHeight(26)
                pri_combo.setFixedWidth(100)
                pri_combo.setStyleSheet(f"""
                    QComboBox {{
                        background-color: {constants.ACCENT};
                        color: {constants.TEXT_SEC};
                        border: 1px solid {constants.SPLITTER_COLOR};
                        border-radius: 4px; padding: 1px 6px; font-size: 11px;
                    }}
                    QComboBox QAbstractItemView {{
                        background-color: {constants.BORDER};
                        color: {constants.TEXT_PRI};
                    }}
                    QComboBox::drop-down {{ border: none; width: 16px; }}
                """)
                _pri_reverse = {"Normal": "normal", "High": "high", "Urgent ⚡": "urgent"}
                pri_combo.currentTextChanged.connect(
                    lambda text, _id=item_id: set_item_priority(
                        self._session_path, _id, _pri_reverse.get(text, "normal")
                    )
                )
                btn_row.addWidget(pri_combo)

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
                        background-color: {bg}; color: {fg};
                        border: 1px solid {color if is_current else constants.SPLITTER_COLOR};
                        border-radius: 4px; padding: 2px 12px; font-size: 12px;
                    }}
                    QPushButton:hover {{
                        background-color: {color}; color: white;
                        border-color: {color};
                    }}
                """)
                btn.clicked.connect(
                    lambda *_, _id=item_id, _rs=rs,
                    _rn=reviewer_note, _fa=frame_annots:
                        self._on_review(_id, _rs, _rn, _fa)
                )
                btn_row.addWidget(btn)

            cl.addLayout(btn_row)

        return card

    # ------------------------------------------------------------------ #
    #  Batch mode                                                          #
    # ------------------------------------------------------------------ #

    def _toggle_batch_mode(self):
        self._batch_mode = not self._batch_mode
        self._checked_ids.clear()
        self._load_session()

    def _on_check(self, checked: bool, item_id: str):
        if checked:
            self._checked_ids.add(item_id)
        else:
            self._checked_ids.discard(item_id)
        self._update_sel_label()

    def _update_sel_label(self):
        n = len(self._checked_ids)
        self._sel_lbl.setText(f"{n} selected")

    def _on_batch_review(self, review_status: str):
        if not self._checked_ids:
            return
        if not self._require_can_review():
            return
        result = self._ask_reviewer_note(review_status, "")
        if result is None:
            return
        note, _annotations = result

        batch_set_review(
            self._session_path, list(self._checked_ids), review_status, note
        )

        # Mirror status to each shot's .meta file
        data = read_session(self._session_path)
        for it in data.get("items", []):
            if it.get("id") in self._checked_ids:
                fp = it.get("file_path", "")
                if fp:
                    try:
                        meta = read_meta(Path(fp))
                        meta["status"] = review_status
                        write_meta(Path(fp), meta)
                        if note:
                            add_note(fp, constants.CURRENT_USER,
                                     f"[{review_status}]  {note}")
                        self.item_reviewed.emit(fp, review_status)
                    except Exception:
                        pass

        self._checked_ids.clear()
        self._batch_mode = False
        self._load_session()

    # ------------------------------------------------------------------ #
    #  Version history viewer                                              #
    # ------------------------------------------------------------------ #

    def _show_history(self, history: list[dict], current_version: int):
        dlg = QDialog(self)
        dlg.setWindowTitle("Version History")
        dlg.setMinimumWidth(500)
        dlg.setAttribute(Qt.WA_StyledBackground, True)
        dlg.setStyleSheet(f"background-color: {constants.BORDER};")

        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(20, 18, 20, 18)
        vl.setSpacing(10)

        title = QLabel(f"Version History  —  {len(history) + 1} versions")
        title.setStyleSheet(
            f"color: {constants.TEXT_PRI}; font-size: 14px; font-weight: bold;"
            f"background: transparent;"
        )
        vl.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        il = QVBoxLayout(inner)
        il.setSpacing(8)

        # Show history oldest→newest
        for entry in sorted(history, key=lambda x: x.get("version", 0)):
            ver    = entry.get("version", "?")
            status = entry.get("review_status", "") or "Pending"
            note   = entry.get("reviewer_note", "")
            fname  = Path(entry.get("file_path", "")).name
            sub_by = entry.get("submitted_by", "")
            sub_at = entry.get("submitted_at", "")[:10]

            row = QFrame()
            row.setFrameShape(QFrame.StyledPanel)
            row.setStyleSheet(f"""
                QFrame {{
                    background-color: {constants.BG};
                    border: 1px solid {constants.SPLITTER_COLOR};
                    border-radius: 4px;
                }}
                QFrame QLabel {{ background: transparent; border: none; }}
            """)
            rl = QVBoxLayout(row)
            rl.setContentsMargins(12, 8, 12, 8)
            rl.setSpacing(3)

            hdr = QHBoxLayout()
            ver_lbl = QLabel(f"v{ver}")
            ver_lbl.setStyleSheet(
                f"color: {constants.ACCENT_HI}; font-weight: bold; font-size: 12px;"
            )
            hdr.addWidget(ver_lbl)
            fname_lbl = QLabel(fname)
            fname_lbl.setStyleSheet(f"color: {constants.TEXT_PRI}; font-size: 12px;")
            hdr.addWidget(fname_lbl, stretch=1)
            status_color = _REVIEW_STATUS_COLORS.get(
                entry.get("review_status", ""), constants.TEXT_SEC
            )
            st_lbl = QLabel(status)
            st_lbl.setStyleSheet(f"color: {status_color}; font-size: 11px;")
            hdr.addWidget(st_lbl)
            rl.addLayout(hdr)

            meta_lbl = QLabel(f"by {sub_by}  ·  {sub_at}")
            meta_lbl.setStyleSheet(f"color: {constants.TEXT_SEC}; font-size: 11px;")
            rl.addWidget(meta_lbl)

            if note:
                note_lbl = QLabel(f"📝  {note}")
                note_lbl.setStyleSheet(
                    f"color: {constants.TEXT_SEC}; font-size: 11px; font-style: italic;"
                )
                note_lbl.setWordWrap(True)
                rl.addWidget(note_lbl)

            il.addWidget(row)

        il.addStretch()
        scroll.setWidget(inner)
        vl.addWidget(scroll)

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(30)
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
        close_btn.clicked.connect(dlg.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        vl.addLayout(btn_row)

        dlg.exec_()

    # ------------------------------------------------------------------ #
    #  Side-by-side comparison                                             #
    # ------------------------------------------------------------------ #

    def _open_compare(self, path_a: str, path_b: str, ver_a: int, ver_b: int):
        from dialogs.compare_dialog import CompareDialog
        dlg = CompareDialog(path_a, path_b, ver_a, ver_b, parent=self)
        dlg.exec_()

    # ------------------------------------------------------------------ #
    #  Slots                                                               #
    # ------------------------------------------------------------------ #

    def _play_file(self, file_path: str):
        if not file_path or not Path(file_path).exists():
            return
        bp = constants.BLAST_PLAYER_PATH
        if bp and Path(str(bp)).is_file():
            try:
                kwargs = {}
                if sys.platform == "win32":
                    kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
                subprocess.Popen([sys.executable, str(bp), file_path], **kwargs)
                return
            except Exception:
                pass
        try:
            if sys.platform == "win32":
                subprocess.Popen(["start", "", file_path], shell=True)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", file_path])
            else:
                subprocess.Popen(["xdg-open", file_path])
        except Exception:
            pass

    def _on_review(self, item_id: str, review_status: str,
                   existing_note: str = "", existing_annotations: list | None = None):
        if not self._require_can_review():
            return

        result = self._ask_reviewer_note(review_status, existing_note, existing_annotations or [])
        if result is None:
            return
        note, annotations = result

        set_item_review(self._session_path, item_id, review_status, note, annotations)

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
                                "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
                            })
                            meta["status_history"] = history
                        write_meta(Path(fp), meta)
                        if note:
                            ann_str = "  ".join(
                                f"[{a['start']}–{a['end']}] {a['note']}"
                                for a in annotations if a.get("note")
                            )
                            full_note = f"{note}  {ann_str}".strip() if ann_str else note
                            add_note(fp, constants.CURRENT_USER,
                                     f"[{review_status}]  {full_note}")
                        self.item_reviewed.emit(fp, review_status)
                    except Exception:
                        pass
                break

        self._load_session()

    def _ask_reviewer_note(self, status: str, existing_note: str = "",
                           existing_annotations: list | None = None):
        """Prompt for an optional reviewer note + optional frame range annotations.

        Returns (note_str, annotations_list) on confirm, or None if cancelled.
        """
        _status_colors = {
            "Approved": constants.SUCCESS,
            "Revision": "#e5a820",
            "On Hold":  constants.FAIL,
        }
        btn_color = _status_colors.get(status, constants.ACCENT_HI)
        annotations = list(existing_annotations or [])

        dlg = QDialog(self)
        dlg.setWindowTitle(status)
        dlg.setAttribute(Qt.WA_StyledBackground, True)
        dlg.setStyleSheet(f"background-color: {constants.BORDER};")
        dlg.setMinimumWidth(440)

        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(20, 18, 20, 18)
        vl.setSpacing(10)

        # Note field
        lbl = QLabel("Reviewer note <i>(optional)</i>:")
        lbl.setStyleSheet(
            f"color: {constants.TEXT_PRI}; font-size: 12px;"
            f"background: transparent; border: none;"
        )
        vl.addWidget(lbl)

        note_edit = QTextEdit()
        note_edit.setPlaceholderText("Add a note for the artist…")
        note_edit.setFixedHeight(72)
        note_edit.setPlainText(existing_note)
        note_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {constants.BG};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px; padding: 4px; font-size: 12px;
            }}
        """)
        vl.addWidget(note_edit)

        # Frame range annotations section
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {constants.SPLITTER_COLOR};")
        vl.addWidget(sep)

        ann_title = QLabel("Frame Range Annotations  <i>(optional)</i>")
        ann_title.setStyleSheet(
            f"color: {constants.TEXT_PRI}; font-size: 12px;"
            f"background: transparent; border: none;"
        )
        vl.addWidget(ann_title)

        # Annotation list container
        ann_container = QWidget()
        ann_container.setStyleSheet("background: transparent;")
        ann_layout = QVBoxLayout(ann_container)
        ann_layout.setContentsMargins(0, 0, 0, 0)
        ann_layout.setSpacing(4)
        vl.addWidget(ann_container)

        def _rebuild_ann_list():
            _clear_layout(ann_layout)
            for i, ann in enumerate(annotations):
                row = QHBoxLayout()
                fr_lbl = QLabel(f"[{ann.get('start', '')}–{ann.get('end', '')}]")
                fr_lbl.setFixedWidth(90)
                fr_lbl.setStyleSheet(
                    f"color: {constants.ACCENT_HI}; font-size: 11px;"
                    f"background: transparent;"
                )
                row.addWidget(fr_lbl)
                note_lbl2 = QLabel(ann.get("note", ""))
                note_lbl2.setStyleSheet(
                    f"color: {constants.TEXT_PRI}; font-size: 11px;"
                    f"background: transparent;"
                )
                note_lbl2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                row.addWidget(note_lbl2, stretch=1)
                del_btn = QPushButton("×")
                del_btn.setFixedSize(20, 20)
                del_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent; color: {constants.FAIL};
                        border: none; font-size: 14px;
                    }}
                    QPushButton:hover {{ color: white; background: {constants.FAIL}; border-radius: 3px; }}
                """)
                del_btn.clicked.connect(lambda *_, _i=i: _remove_ann(_i))
                row.addWidget(del_btn)
                w = QWidget()
                w.setStyleSheet("background: transparent;")
                w.setLayout(row)
                ann_layout.addWidget(w)

        def _remove_ann(idx: int):
            annotations.pop(idx)
            _rebuild_ann_list()

        _rebuild_ann_list()

        # Add annotation row
        add_row = QHBoxLayout()
        start_spin = QSpinBox()
        start_spin.setRange(0, 99999)
        start_spin.setPrefix("Fr ")
        start_spin.setFixedWidth(80)
        start_spin.setFixedHeight(28)
        start_spin.setStyleSheet(f"""
            QSpinBox {{
                background: {constants.BG}; color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR}; border-radius: 4px;
                padding: 2px 4px; font-size: 11px;
            }}
        """)
        end_spin = QSpinBox()
        end_spin.setRange(0, 99999)
        end_spin.setPrefix("→ ")
        end_spin.setFixedWidth(80)
        end_spin.setFixedHeight(28)
        end_spin.setStyleSheet(start_spin.styleSheet())

        from PyQt5.QtWidgets import QLineEdit as _LE
        ann_note_edit = _LE()
        ann_note_edit.setPlaceholderText("Note for these frames…")
        ann_note_edit.setFixedHeight(28)
        ann_note_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {constants.BG}; color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR}; border-radius: 4px;
                padding: 2px 6px; font-size: 11px;
            }}
        """)

        add_ann_btn = QPushButton("+ Add")
        add_ann_btn.setFixedHeight(28)
        add_ann_btn.setFixedWidth(54)
        add_ann_btn.setStyleSheet(f"""
            QPushButton {{
                background: {constants.ACCENT};
                color: {constants.TEXT_PRI};
                border: none; border-radius: 4px; font-size: 11px;
            }}
            QPushButton:hover {{ background: {constants.ACCENT_HI}; color: white; }}
        """)

        def _add_annotation():
            note_val = ann_note_edit.text().strip()
            if not note_val:
                return
            annotations.append({
                "start": start_spin.value(),
                "end":   end_spin.value(),
                "note":  note_val,
            })
            ann_note_edit.clear()
            _rebuild_ann_list()

        add_ann_btn.clicked.connect(_add_annotation)
        ann_note_edit.returnPressed.connect(_add_annotation)

        add_row.addWidget(start_spin)
        add_row.addWidget(end_spin)
        add_row.addWidget(ann_note_edit, stretch=1)
        add_row.addWidget(add_ann_btn)
        vl.addLayout(add_row)

        # Dialog buttons
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background-color: {constants.SPLITTER_COLOR};")
        vl.addWidget(sep2)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(30)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT}; color: {constants.TEXT_SEC};
                border: none; border-radius: 4px; padding: 2px 14px;
            }}
            QPushButton:hover {{
                background-color: {constants.SPLITTER_COLOR}; color: {constants.TEXT_PRI};
            }}
        """)
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)

        confirm_btn = QPushButton(status)
        confirm_btn.setFixedHeight(30)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_color}; color: white;
                border: none; border-radius: 4px;
                padding: 2px 14px; font-weight: bold;
            }}
        """)
        confirm_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(confirm_btn)

        vl.addLayout(btn_row)

        if dlg.exec_() == QDialog.Accepted:
            return note_edit.toPlainText().strip(), annotations
        return None

    def _on_mark_complete(self):
        if not self._require_admin():
            return
        mark_completed(self._session_path)
        self._load_session()

    # ------------------------------------------------------------------ #
    #  Permission gates                                                    #
    # ------------------------------------------------------------------ #

    def _require_can_review(self) -> bool:
        if constants.can_review():
            return True
        return self._require_admin()

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


# ── Utility ───────────────────────────────────────────────────────────────── #

def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear_layout(item.layout())
