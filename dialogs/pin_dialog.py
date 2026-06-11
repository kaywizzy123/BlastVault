"""
pin_dialog.py — Styled admin PIN dialogs.

NoPinDialog     — info-only: tells the user no PIN is set, contact admin.
PinInputDialog  — single-field, enter & optionally verify a PIN.
PinSetupDialog  — two-field, create a new PIN (both fields must match).
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

from core import constants


# ──────────────────────────────────────────────────────────────────────────── #
#  Info-only: no PIN set                                                        #
# ──────────────────────────────────────────────────────────────────────────── #

class NoPinDialog(QDialog):
    """Styled info dialog shown to registry artists when no admin PIN exists."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("No Admin PIN")
        self.setFixedWidth(360)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setStyleSheet(f"background-color: {constants.BORDER};")
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self._ok_btn = QPushButton("OK")
        self._ok_btn.setFixedHeight(32)
        self._ok_btn.setMinimumWidth(90)
        self._ok_btn.setCursor(Qt.PointingHandCursor)
        self._ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT_HI};
                color: white; border: none; border-radius: 4px;
                padding: 4px 20px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #1a95e8; }}
        """)

    def create_layout(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(0)

        icon_lbl = QLabel()
        pix = QPixmap(str(constants.ICONS_DIR / "lock.png"))
        if not pix.isNull():
            icon_lbl.setPixmap(
                pix.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent;")
        outer.addWidget(icon_lbl)
        outer.addSpacing(10)

        title_lbl = QLabel("No Admin PIN Set")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(f"""
            font-size: 16px; font-weight: bold;
            color: {constants.TEXT_PRI}; background: transparent;
        """)
        outer.addWidget(title_lbl)
        outer.addSpacing(8)

        msg_lbl = QLabel("An admin PIN hasn't been configured yet.\nAsk your admin to set one in Settings.")
        msg_lbl.setAlignment(Qt.AlignCenter)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"""
            font-size: 12px; color: {constants.TEXT_SEC};
            background: transparent; padding: 0px 4px;
        """)
        outer.addWidget(msg_lbl)
        outer.addSpacing(22)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._ok_btn)
        btn_row.addStretch()
        outer.addLayout(btn_row)

    def create_connections(self):
        self._ok_btn.clicked.connect(self.accept)


# ──────────────────────────────────────────────────────────────────────────── #
#  Shared base                                                                  #
# ──────────────────────────────────────────────────────────────────────────── #

class _PinBase(QDialog):
    """Layout skeleton shared by both PIN dialogs."""

    _ICON = "lock.png"

    def __init__(self, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        self._title    = title
        self._subtitle = subtitle
        self.setWindowTitle(title)
        self.setFixedWidth(380)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setStyleSheet(f"background-color: {constants.BORDER};")
        self._accepted_pin = ""
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self._error_lbl = QLabel()
        self._error_lbl.setAlignment(Qt.AlignCenter)
        self._error_lbl.setWordWrap(True)
        self._error_lbl.setFixedHeight(18)
        self._error_lbl.setStyleSheet(f"""
            color: {constants.FAIL}; background: transparent; font-size: 11px;
        """)
        self._error_lbl.setVisible(False)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedHeight(32)
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT};
                color: {constants.TEXT_SEC}; border: none; border-radius: 4px; padding: 4px 16px;
            }}
            QPushButton:hover {{
                background-color: {constants.SPLITTER_COLOR}; color: {constants.TEXT_PRI};
            }}
        """)

        self._confirm_btn = QPushButton("Confirm")
        self._confirm_btn.setFixedHeight(32)
        self._confirm_btn.setCursor(Qt.PointingHandCursor)
        self._confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.ACCENT_HI};
                color: white; border: none; border-radius: 4px;
                padding: 4px 20px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #1a95e8; }}
        """)

    def create_layout(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(0)

        icon_lbl = QLabel()
        pix = QPixmap(str(constants.ICONS_DIR / self._ICON))
        if not pix.isNull():
            icon_lbl.setPixmap(
                pix.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent;")
        outer.addWidget(icon_lbl)
        outer.addSpacing(10)

        title_lbl = QLabel(self._title)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(f"""
            font-size: 16px; font-weight: bold;
            color: {constants.TEXT_PRI}; background: transparent;
        """)
        outer.addWidget(title_lbl)
        outer.addSpacing(6)

        sub_lbl = QLabel(self._subtitle)
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet(f"""
            font-size: 11px; color: {constants.TEXT_SEC};
            background: transparent; padding: 0px 4px;
        """)
        outer.addWidget(sub_lbl)
        outer.addSpacing(18)

        self._fields_layout = QVBoxLayout()
        self._fields_layout.setSpacing(6)
        outer.addLayout(self._fields_layout)

        outer.addSpacing(6)
        outer.addWidget(self._error_lbl)
        outer.addSpacing(14)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._confirm_btn)
        outer.addLayout(btn_row)

    def create_connections(self):
        self._cancel_btn.clicked.connect(self.reject)
        self._confirm_btn.clicked.connect(self._on_confirm)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _on_confirm(self):
        raise NotImplementedError

    def _show_error(self, msg: str):
        self._error_lbl.setText(msg)
        self._error_lbl.setVisible(True)

    def _clear_error(self):
        self._error_lbl.setVisible(False)

    def _make_field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; background: transparent; font-size: 11px;"
        )
        return lbl

    def _make_pin_field(self, placeholder="Enter PIN…") -> QLineEdit:
        field = QLineEdit()
        field.setEchoMode(QLineEdit.Password)
        field.setPlaceholderText(placeholder)
        field.setFixedHeight(34)
        field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {constants.BG};
                color: {constants.TEXT_PRI};
                border: 1px solid {constants.SPLITTER_COLOR};
                border-radius: 4px; padding: 4px 10px;
                font-size: 13px; letter-spacing: 2px;
            }}
            QLineEdit:focus {{ border: 1px solid {constants.ACCENT_HI}; }}
        """)
        return field

    def get_pin(self):
        """Run the dialog.

        Returns ``(pin, True)`` on accept, ``("", False)`` on cancel/close.
        """
        result = self.exec_()
        return (self._accepted_pin, result == QDialog.Accepted)


# ──────────────────────────────────────────────────────────────────────────── #
#  Single-field: verify an existing PIN                                         #
# ──────────────────────────────────────────────────────────────────────────── #

class PinInputDialog(_PinBase):
    """Single password field.

    If *verify_fn* is provided (``callable(pin) -> bool``), the dialog
    validates the PIN inline and stays open on failure.  When *verify_fn*
    is ``None``, any non-empty input is accepted.
    """

    def __init__(
        self,
        title="Admin PIN",
        subtitle="Enter the admin PIN to unlock status editing.",
        verify_fn=None,
        parent=None,
    ):
        self._verify_fn = verify_fn
        super().__init__(title, subtitle, parent)

    def create_widgets(self):
        super().create_widgets()
        self._confirm_btn.setText("Unlock")
        self._pin_field = self._make_pin_field("Enter PIN…")

    def create_layout(self):
        super().create_layout()
        self._fields_layout.addWidget(self._make_field_label("PIN"))
        self._fields_layout.addWidget(self._pin_field)

    def create_connections(self):
        super().create_connections()
        self._pin_field.returnPressed.connect(self._on_confirm)

    def _on_confirm(self):
        pin = self._pin_field.text()
        if not pin:
            self._show_error("Please enter your PIN.")
            return
        if self._verify_fn and not self._verify_fn(pin):
            self._show_error("Incorrect PIN — please try again.")
            self._pin_field.clear()
            self._pin_field.setFocus()
            return
        self._accepted_pin = pin
        self.accept()


# ──────────────────────────────────────────────────────────────────────────── #
#  Two-field: create a new PIN                                                  #
# ──────────────────────────────────────────────────────────────────────────── #

class PinSetupDialog(_PinBase):
    """Two password fields — new PIN must match the confirmation field."""

    def __init__(self, parent=None):
        super().__init__(
            "Set Admin PIN",
            "No admin PIN has been set.\n"
            "Create a PIN to enable status editing.",
            parent,
        )

    def create_widgets(self):
        super().create_widgets()
        self._confirm_btn.setText("Set PIN")
        self._pin_field     = self._make_pin_field("New PIN…")
        self._confirm_field = self._make_pin_field("Confirm PIN…")

    def create_layout(self):
        super().create_layout()
        self._fields_layout.addWidget(self._make_field_label("New PIN"))
        self._fields_layout.addWidget(self._pin_field)
        self._fields_layout.addSpacing(6)
        self._fields_layout.addWidget(self._make_field_label("Confirm PIN"))
        self._fields_layout.addWidget(self._confirm_field)

    def create_connections(self):
        super().create_connections()
        self._pin_field.returnPressed.connect(self._confirm_field.setFocus)
        self._confirm_field.returnPressed.connect(self._on_confirm)

    def _on_confirm(self):
        pin     = self._pin_field.text()
        confirm = self._confirm_field.text()
        if not pin:
            self._show_error("Please enter a PIN.")
            return
        if pin != confirm:
            self._show_error("PINs do not match — please try again.")
            self._confirm_field.clear()
            self._confirm_field.setFocus()
            return
        self._accepted_pin = pin
        self.accept()
