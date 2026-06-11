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
        self._note = note
        self._on_delete = on_delete
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {constants.BG};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 6px;
            }}
        """)
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        date_str = self._note.get("date", "")
        try:
            dt = datetime.datetime.fromisoformat(date_str)
            date_str = dt.strftime("%Y-%m-%d  %H:%M")
        except Exception:
            pass

        self._header_lbl = QLabel(f"{self._note.get('author', 'Unknown')}  •  {date_str}")
        self._header_lbl.setStyleSheet(
            f"background: transparent; border: none;"
            f"color: {constants.ACCENT_HI}; font-size: 11px; font-weight: bold;"
        )

        self._del_btn = None
        if self._on_delete is not None:
            self._note_id = self._note.get("id", "")
            self._del_btn = QPushButton()
            self._del_btn.setIcon(QIcon(str(constants.ICONS_DIR / "bin.png")))
            self._del_btn.setIconSize(QSize(14, 14))
            self._del_btn.setFixedSize(20, 20)
            self._del_btn.setCursor(Qt.PointingHandCursor)
            self._del_btn.setToolTip("Delete note")
            self._del_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 3px;
                }}
                QPushButton:hover {{
                    background-color: {constants.FAIL};
                }}
            """)

        self._content_lbl = QLabel(self._note.get("content", ""))
        self._content_lbl.setWordWrap(True)
        self._content_lbl.setStyleSheet(
            f"background: transparent; border: none;"
            f"color: {constants.TEXT_PRI}; font-size: 12px;"
        )
        self._content_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def create_layout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(4)
        header_row.addWidget(self._header_lbl, stretch=1)
        if self._del_btn is not None:
            header_row.addWidget(self._del_btn)

        layout.addLayout(header_row)
        layout.addWidget(self._content_lbl)

    def create_connections(self):
        if self._del_btn is not None:
            self._del_btn.clicked.connect(lambda: self._on_delete(self._note_id))


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
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self._icon_lbl = QLabel()
        pix = QPixmap(str(constants.ICONS_DIR / "add_note.png"))
        if not pix.isNull():
            self._icon_lbl.setPixmap(
                pix.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setStyleSheet("background: transparent;")

        self._title_lbl = QLabel("Add Note")
        self._title_lbl.setAlignment(Qt.AlignCenter)
        self._title_lbl.setStyleSheet(f"""
            font-size: 15px; font-weight: bold;
            color: {constants.TEXT_PRI}; background: transparent;
        """)

        self._sub_lbl = QLabel("Sign your note with your name.")
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        self._sub_lbl.setStyleSheet(f"""
            font-size: 11px; color: {constants.TEXT_SEC}; background: transparent;
        """)

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
            QLineEdit:focus {{ border: 1px solid {constants.ACCENT_HI}; }}
        """)

        self._error_lbl = QLabel()
        self._error_lbl.setAlignment(Qt.AlignCenter)
        self._error_lbl.setFixedHeight(16)
        self._error_lbl.setStyleSheet(
            f"color: {constants.FAIL}; background: transparent; font-size: 11px;"
        )
        self._error_lbl.setVisible(False)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedHeight(30)
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT};
                color: {constants.TEXT_SEC};
                border: none; border-radius: 4px; padding: 4px 14px;
            }}
            QPushButton:hover {{
                background-color: {constants.SPLITTER_COLOR};
                color: {constants.TEXT_PRI};
            }}
        """)

        self._add_btn = QPushButton("Add Note")
        self._add_btn.setFixedHeight(30)
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT_HI};
                color: white; border: none; border-radius: 4px;
                padding: 4px 16px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #1a95e8; }}
        """)

    def create_layout(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(0)

        outer.addWidget(self._icon_lbl)
        outer.addSpacing(10)
        outer.addWidget(self._title_lbl)
        outer.addSpacing(4)
        outer.addWidget(self._sub_lbl)
        outer.addSpacing(16)

        name_lbl = QLabel("Your name")
        name_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; background: transparent; font-size: 11px;"
        )
        outer.addWidget(name_lbl)
        outer.addSpacing(4)
        outer.addWidget(self._name_field)
        outer.addSpacing(4)
        outer.addWidget(self._error_lbl)
        outer.addSpacing(14)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._add_btn)
        outer.addLayout(btn_row)

    def create_connections(self):
        self._name_field.returnPressed.connect(self._on_confirm)
        self._cancel_btn.clicked.connect(self.reject)
        self._add_btn.clicked.connect(self._on_confirm)

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

        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self._load_notes()

    # ------------------------------------------------------------------ #
    #  UI construction                                                      #
    # ------------------------------------------------------------------ #

    def create_widgets(self):
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

        self._note_input = None
        self._add_btn = None
        if constants.can_review():
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
                QTextEdit:focus {{ border: 1px solid {constants.ACCENT_HI}; }}
            """)

            self._add_btn = QPushButton("Add Note")
            self._add_btn.setFixedHeight(28)
            self._add_btn.setMinimumWidth(90)
            self._add_btn.setCursor(Qt.PointingHandCursor)
            self._add_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {constants.ACCENT_HI};
                    color: white; border: none; border-radius: 4px;
                    padding: 4px 14px; font-weight: bold;
                }}
                QPushButton:hover {{ background-color: #1a95e8; }}
            """)

    def create_layout(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(8)

        main.addWidget(self._scroll, stretch=1)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {constants.SPLITTER_COLOR};")
        main.addWidget(sep)

        if self._note_input is not None:
            main.addWidget(self._note_input)
            btn_row = QHBoxLayout()
            btn_row.setContentsMargins(0, 0, 0, 0)
            btn_row.addStretch()
            btn_row.addWidget(self._add_btn)
            main.addLayout(btn_row)
        else:
            locked_lbl = QLabel("Unlock admin mode to add notes.")
            locked_lbl.setAlignment(Qt.AlignCenter)
            locked_lbl.setStyleSheet(
                f"color: {constants.TEXT_SEC}; background: transparent; font-size: 11px;"
            )
            main.addWidget(locked_lbl)

    def create_connections(self):
        if self._add_btn is not None:
            self._add_btn.clicked.connect(self._on_add_note)

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
            # Delete is admin-only; adding notes is reviewer+ (handled in _build_ui)
            on_del = self._on_delete_note if constants.can_admin() else None
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

        add_note(self._file_path, constants.CURRENT_USER, content)
        self._note_input.clear()
        self._load_notes()
