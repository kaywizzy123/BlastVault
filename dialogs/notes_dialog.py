"""
NotesDialog — per-asset review notes viewer / editor.

Everyone can read notes.  Only admins (unlocked state) can add notes.
Author name is prompted each time a note is submitted.
"""
import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QScrollArea, QWidget, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QPixmap

from core import constants
from core.constants import version_key
from core.notes import read_notes, add_note, delete_note


# ──────────────────────────────────────────────────────────────────────────── #
#  Note card widget                                                              #
# ──────────────────────────────────────────────────────────────────────────── #

class _NoteCard(QWidget):
    """Visual card for a single note entry."""

    def __init__(self, note: dict, on_delete=None, parent=None):
        """
        *on_delete*: callable(note_id) — called when the delete button is
        clicked.  Pass None (or omit) to hide the delete button.
        """
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {constants.BG};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # ── Header row: author • date  [×] ──────────────────────────────
        date_str = note.get("date", "")
        try:
            dt = datetime.datetime.fromisoformat(date_str)
            date_str = dt.strftime("%Y-%m-%d  %H:%M")
        except Exception:
            pass

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(4)

        header = QLabel(f"{note.get('author', 'Unknown')}  •  {date_str}")
        header.setStyleSheet(
            f"background: transparent; border: none;"
            f"color: {constants.ACCENT_HI}; font-size: 11px; font-weight: bold;"
        )
        header_row.addWidget(header, stretch=1)

        if on_delete is not None:
            note_id = note.get("id", "")
            del_btn = QPushButton()
            del_btn.setIcon(QIcon(str(constants.ICONS_DIR / "bin.png")))
            del_btn.setIconSize(QSize(14, 14))
            del_btn.setFixedSize(20, 20)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setToolTip("Delete note")
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 3px;
                }}
                QPushButton:hover {{
                    background-color: {constants.FAIL};
                }}
            """)
            del_btn.clicked.connect(lambda: on_delete(note_id))
            header_row.addWidget(del_btn)

        content_label = QLabel(note.get("content", ""))
        content_label.setWordWrap(True)
        content_label.setStyleSheet(
            f"background: transparent; border: none;"
            f"color: {constants.TEXT_PRI}; font-size: 12px;"
        )
        content_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout.addLayout(header_row)
        layout.addWidget(content_label)


# ──────────────────────────────────────────────────────────────────────────── #
#  Author name dialog                                                            #
# ──────────────────────────────────────────────────────────────────────────── #

class _AuthorInputDialog(QDialog):
    """Styled dialog that prompts for the note author's name."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Note")
        self.setFixedWidth(340)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setStyleSheet(f"background-color: {constants.BORDER};")
        self._author = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(0)

        # ── Icon ─────────────────────────────────────────────────────────
        icon_lbl = QLabel()
        pix = QPixmap(str(constants.ICONS_DIR / "add_note.png"))
        if not pix.isNull():
            icon_lbl.setPixmap(
                pix.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent;")
        outer.addWidget(icon_lbl)
        outer.addSpacing(10)

        # ── Title ─────────────────────────────────────────────────────────
        title_lbl = QLabel("Add Note")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(f"""
            font-size: 15px;
            font-weight: bold;
            color: {constants.TEXT_PRI};
            background: transparent;
        """)
        outer.addWidget(title_lbl)
        outer.addSpacing(4)

        # ── Subtitle ──────────────────────────────────────────────────────
        sub_lbl = QLabel("Sign your note with your name.")
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setStyleSheet(f"""
            font-size: 11px;
            color: {constants.TEXT_SEC};
            background: transparent;
        """)
        outer.addWidget(sub_lbl)
        outer.addSpacing(16)

        # ── Name field ────────────────────────────────────────────────────
        name_lbl = QLabel("Your name")
        name_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; background: transparent; font-size: 11px;"
        )
        outer.addWidget(name_lbl)
        outer.addSpacing(4)

        self._name_field = QLineEdit()
        self._name_field.setPlaceholderText("e.g.  John Smith")
        self._name_field.setFixedHeight(34)
        self._name_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {constants.BG};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {constants.ACCENT_HI};
            }}
        """)
        self._name_field.returnPressed.connect(self._on_confirm)
        outer.addWidget(self._name_field)

        # ── Error label ───────────────────────────────────────────────────
        self._error_lbl = QLabel()
        self._error_lbl.setAlignment(Qt.AlignCenter)
        self._error_lbl.setFixedHeight(16)
        self._error_lbl.setStyleSheet(
            f"color: {constants.FAIL}; background: transparent; font-size: 11px;"
        )
        self._error_lbl.setVisible(False)
        outer.addSpacing(4)
        outer.addWidget(self._error_lbl)
        outer.addSpacing(14)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(30)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT};
                color: {constants.TEXT_SEC};
                border: none;
                border-radius: 4px;
                padding: 4px 14px;
            }}
            QPushButton:hover {{
                background-color: {constants.SPLITTER_COLOR};
                color: {constants.TEXT_PRI};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)

        add_btn = QPushButton("Add Note")
        add_btn.setFixedHeight(30)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT_HI};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #1a95e8;
            }}
        """)
        add_btn.clicked.connect(self._on_confirm)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(add_btn)
        outer.addLayout(btn_row)

    def _on_confirm(self):
        name = self._name_field.text().strip()
        if not name:
            self._error_lbl.setText("Please enter your name.")
            self._error_lbl.setVisible(True)
            return
        self._author = name
        self.accept()

    def get_author(self):
        """Run the dialog. Returns ``(author, True)`` on accept, ``("", False)`` on cancel."""
        result = self.exec_()
        return (self._author, result == QDialog.Accepted)


# ──────────────────────────────────────────────────────────────────────────── #
#  Notes dialog                                                                  #
# ──────────────────────────────────────────────────────────────────────────── #

class NotesDialog(QDialog):

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self._file_path = file_path

        p = Path(file_path)
        base, _ = version_key(p.stem)
        asset_name = base if base is not None else p.stem

        self.setWindowTitle(f"Notes — {asset_name}")
        self.setMinimumWidth(440)
        self.setMinimumHeight(320)
        self.resize(480, 520)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {constants.BORDER};")
        # Remove the ? help button; allow the user to maximise the window
        self.setWindowFlags(
            (self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            | Qt.WindowMaximizeButtonHint
        )

        self._build_ui()
        self._load_notes()

    # ------------------------------------------------------------------ #
    #  UI construction                                                      #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(8)

        # ── Scrollable notes list ────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("background: transparent;")

        self._cards_widget = QWidget()
        self._cards_widget.setStyleSheet("background: transparent;")
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(0, 0, 4, 0)
        self._cards_layout.setSpacing(6)
        self._scroll.setWidget(self._cards_widget)

        main.addWidget(self._scroll, stretch=1)

        # ── Separator ────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {constants.SPLITTER_COLOR};")
        main.addWidget(sep)

        # ── Input area (admin only) / locked message ─────────────────────
        if not constants.STATUS_LOCKED:
            self._note_input = QTextEdit()
            self._note_input.setPlaceholderText("Write a note…")
            self._note_input.setFixedHeight(80)
            self._note_input.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {constants.BG};
                    color: {constants.TEXT_PRI};
                    border: 1px solid {constants.SPLITTER_COLOR};
                    border-radius: 4px;
                    padding: 6px;
                }}
                QTextEdit:focus {{
                    border: 1px solid {constants.ACCENT_HI};
                }}
            """)
            main.addWidget(self._note_input)

            btn_row = QHBoxLayout()
            btn_row.setContentsMargins(0, 0, 0, 0)
            btn_row.addStretch()

            add_btn = QPushButton("Add Note")
            add_btn.setFixedHeight(28)
            add_btn.setMinimumWidth(90)
            add_btn.setCursor(Qt.PointingHandCursor)
            add_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {constants.ACCENT_HI};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 14px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #1a95e8;
                }}
            """)
            add_btn.clicked.connect(self._on_add_note)
            btn_row.addWidget(add_btn)
            main.addLayout(btn_row)

        else:
            locked_lbl = QLabel("Unlock to add notes.")
            locked_lbl.setAlignment(Qt.AlignCenter)
            locked_lbl.setStyleSheet(
                f"color: {constants.TEXT_SEC}; background: transparent; font-size: 11px;"
            )
            main.addWidget(locked_lbl)

    # ------------------------------------------------------------------ #
    #  Notes list                                                           #
    # ------------------------------------------------------------------ #

    def _load_notes(self):
        """Rebuild the notes card list from disk."""
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        notes = read_notes(self._file_path)

        if not notes:
            empty = QLabel("No notes yet.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                f"color: {constants.TEXT_SEC}; background: transparent; padding: 20px;"
            )
            self._cards_layout.addWidget(empty)
        else:
            # Pass delete callback to each card only when admin is unlocked
            on_del = self._on_delete_note if not constants.STATUS_LOCKED else None
            for note in reversed(notes):   # newest first
                self._cards_layout.addWidget(_NoteCard(note, on_delete=on_del))

        self._cards_layout.addStretch()
        self._scroll.verticalScrollBar().setValue(0)

    # ------------------------------------------------------------------ #
    #  Slot                                                                #
    # ------------------------------------------------------------------ #

    def _on_delete_note(self, note_id: str):
        """Delete the note with *note_id* and refresh the list."""
        delete_note(self._file_path, note_id)
        self._load_notes()

    def _on_add_note(self):
        content = self._note_input.toPlainText().strip()
        if not content:
            return

        dlg = _AuthorInputDialog(self)
        author, ok = dlg.get_author()
        if not ok:
            return

        add_note(self._file_path, author, content)
        self._note_input.clear()
        self._load_notes()
