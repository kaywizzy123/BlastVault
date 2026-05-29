import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap

from core import constants


class SplashScreen(QWidget):
    """Frameless splash screen shown while BlastVault initialises.

    Usage
    -----
    splash = SplashScreen()
    splash.show()
    QApplication.processEvents()

    # ... do work, call splash.set_progress(value, message) along the way ...

    splash.close()
    """

    MIN_DISPLAY_MS = 2000   # minimum milliseconds the splash stays visible

    def __init__(self):
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen,
        )
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedSize(420, 290)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {constants.BG};
                border: 1px solid {constants.SPLITTER_COLOR};
            }}
        """)

        # ── Logo ─────────────────────────────────────────────────────────
        self._logo_lbl = QLabel()
        self._logo_lbl.setAlignment(Qt.AlignCenter)
        self._logo_lbl.setStyleSheet("border: none; background: transparent;")
        pix = QPixmap(constants.ICON)
        if not pix.isNull():
            self._logo_lbl.setPixmap(
                pix.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        # ── App name ─────────────────────────────────────────────────────
        self._title_lbl = QLabel("BlastVault")
        self._title_lbl.setAlignment(Qt.AlignCenter)
        self._title_lbl.setStyleSheet(f"""
            border: none;
            background: transparent;
            color: {constants.TEXT_PRI};
            font-size: 26px;
            font-weight: bold;
        """)

        # ── Studio name ───────────────────────────────────────────────────
        self._studio_lbl = QLabel(constants.STUDIO_NAME)
        self._studio_lbl.setAlignment(Qt.AlignCenter)
        self._studio_lbl.setStyleSheet(f"""
            border: none;
            background: transparent;
            color: {constants.TEXT_SEC};
            font-size: 11px;
            letter-spacing: 1px;
        """)

        # ── Progress bar ─────────────────────────────────────────────────
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(5)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background: {constants.SPLITTER_COLOR};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: {constants.ACCENT_HI};
                border-radius: 2px;
            }}
        """)

        # ── Status message ────────────────────────────────────────────────
        self._status_lbl = QLabel("Starting…")
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setStyleSheet(f"""
            border: none;
            background: transparent;
            color: {constants.TEXT_SEC};
            font-size: 11px;
        """)

        # ── Layout ────────────────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 20)
        layout.setSpacing(0)

        layout.addStretch()
        layout.addWidget(self._logo_lbl)
        layout.addSpacing(10)
        layout.addWidget(self._title_lbl)
        layout.addSpacing(6)
        layout.addWidget(self._studio_lbl)
        layout.addStretch()
        layout.addWidget(self._bar)
        layout.addSpacing(6)
        layout.addWidget(self._status_lbl)

        # ── Centre on primary screen ──────────────────────────────────────
        screen = QApplication.desktop().availableGeometry()
        self.move(
            screen.center().x() - self.width()  // 2,
            screen.center().y() - self.height() // 2,
        )

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def set_progress(self, value: int, message: str = "") -> None:
        """Update the progress bar and status text, then repaint immediately."""
        self._bar.setValue(value)
        if message:
            self._status_lbl.setText(message)
        QApplication.processEvents()

    def set_studio_name(self, name: str) -> None:
        """Update the studio name label (call after config is loaded)."""
        self._studio_lbl.setText(name)
        QApplication.processEvents()


# ── Standalone preview ────────────────────────────────────────────────────── #
if __name__ == "__main__":
    from core.styles import qt_argv

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(qt_argv())
    app.setStyle("Fusion")

    splash = SplashScreen()
    splash.show()
    QApplication.processEvents()

    # Simulate staged loading so the splash can be visually previewed
    _steps = [
        (10,  "Loading configuration…"),
        (35,  "Building interface…"),
        (60,  "Setting up layout…"),
        (80,  "Connecting signals…"),
        (95,  "Restoring catalogs…"),
        (100, "Ready!"),
    ]
    _idx = [0]  # mutable counter captured by closure

    def _next_step():
        if _idx[0] < len(_steps):
            value, msg = _steps[_idx[0]]
            splash.set_progress(value, msg)
            _idx[0] += 1
            QTimer.singleShot(400, _next_step)
        else:
            QTimer.singleShot(600, app.quit)

    QTimer.singleShot(300, _next_step)
    app.exec_()
