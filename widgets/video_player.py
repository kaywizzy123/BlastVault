"""Embedded video player dialog (OpenCV / ffmpeg backend).

cv2.VideoCapture decodes via ffmpeg — supports H.264, H.265, ProRes, VP9,
MKV, MOV, AVI, and essentially every format ffmpeg knows about.
No DirectShow codec packs required.

Note: Audio is not played (video-only preview).

Controls: Space / ▶ button  — play / pause
          Seek slider       — scrub
          Esc               — close
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel, QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

from core import constants


def _ms_to_hms(ms: int) -> str:
    s    = ms // 1000
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class _VideoLabel(QLabel):
    """QLabel that scales an OpenCV BGR frame to fit, keeping aspect ratio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background: #000000;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def show_frame(self, frame_bgr):
        h, w = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        # strides[0] = bytes per row (handles any alignment OpenCV may add)
        qimg = QImage(
            frame_rgb.data, w, h,
            frame_rgb.strides[0],
            QImage.Format_RGB888,
        )
        pixmap = QPixmap.fromImage(qimg)
        self.setPixmap(
            pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.FastTransformation)
        )


class VideoPlayerDialog(QDialog):
    """Video preview dialog backed by OpenCV (ffmpeg)."""

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(Path(path).name)
        self.setMinimumSize(640, 400)
        self.resize(900, 560)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.setStyleSheet("background-color: #111111;")
        self._path   = path
        self._cap    = None
        self._playing = False
        self._slider_dragging = False

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            cap.release()
            self._setup_error_ui(f"Cannot open file:\n{Path(path).name}")
            return

        self._cap          = cap
        self._fps          = cap.get(cv2.CAP_PROP_FPS) or 24.0
        self._total_frames = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
        self._current_frame = 0

        self._setup_player_ui()
        self._seek_to(0)          # show first frame
        self._start_playback()    # auto-play

    # ------------------------------------------------------------------ #
    #  UI builders                                                         #
    # ------------------------------------------------------------------ #

    def _setup_player_ui(self):
        self._video_lbl = _VideoLabel()

        self._play_btn = QPushButton("▶")
        self._play_btn.setFixedSize(36, 28)
        self._play_btn.setStyleSheet(
            f"QPushButton {{ background: {constants.ACCENT}; color: {constants.TEXT_PRI};"
            f" border-radius: 4px; font-size: 14px; }}"
            f"QPushButton:hover {{ background: {constants.ACCENT_HI}; }}"
        )
        self._play_btn.setCursor(Qt.PointingHandCursor)
        self._play_btn.clicked.connect(self._toggle_play)

        self._seek = QSlider(Qt.Horizontal)
        self._seek.setRange(0, self._total_frames - 1)
        self._seek.setValue(0)
        self._seek.setCursor(Qt.PointingHandCursor)
        self._seek.setStyleSheet(
            f"QSlider {{ background: transparent; }}"
            f"QSlider::groove:horizontal {{ background: {constants.SPLITTER_COLOR};"
            f" height: 4px; border-radius: 2px; }}"
            f"QSlider::handle:horizontal {{ background: {constants.ACCENT_HI};"
            f" width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }}"
            f"QSlider::sub-page:horizontal {{ background: {constants.ACCENT};"
            f" border-radius: 2px; }}"
        )
        self._seek.sliderPressed.connect(self._on_slider_pressed)
        self._seek.sliderReleased.connect(self._on_slider_released)
        self._seek.sliderMoved.connect(self._seek_to)

        total_ms = int(self._total_frames * 1000 / self._fps)
        self._time_lbl = QLabel(f"00:00:00 / {_ms_to_hms(total_ms)}")
        self._time_lbl.setStyleSheet(
            f"color: {constants.TEXT_SEC}; background: transparent; font-size: 11px;"
        )

        hint = QLabel("Space — play/pause  ·  Esc — close  ·  video preview (no audio)")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(
            f"color: {constants.TEXT_SEC}; background: transparent; font-size: 10px;"
        )

        ctrl = QHBoxLayout()
        ctrl.setContentsMargins(6, 2, 6, 2)
        ctrl.setSpacing(6)
        ctrl.addWidget(self._play_btn)
        ctrl.addWidget(self._seek, 1)
        ctrl.addWidget(self._time_lbl)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._video_lbl, 1)
        layout.addLayout(ctrl)
        layout.addWidget(hint)

        interval = max(1, int(1000 / self._fps))
        self._timer = QTimer(self)
        self._timer.setInterval(interval)
        self._timer.timeout.connect(self._advance_frame)

    def _setup_error_ui(self, message: str):
        lbl = QLabel(f"⚠  {message}")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            "color: #ff6b6b; background: transparent; font-size: 13px; padding: 24px;"
        )
        layout = QVBoxLayout(self)
        layout.addWidget(lbl)

    # ------------------------------------------------------------------ #
    #  Playback                                                            #
    # ------------------------------------------------------------------ #

    def _seek_to(self, frame_idx: int):
        if self._cap is None:
            return
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self._cap.read()
        if ret:
            self._video_lbl.show_frame(frame)
        self._current_frame = frame_idx
        self._refresh_timecode()

    def _advance_frame(self):
        if self._slider_dragging or self._cap is None:
            return
        ret, frame = self._cap.read()
        if not ret:
            self._stop_playback()
            return
        self._video_lbl.show_frame(frame)
        self._current_frame += 1
        self._refresh_timecode()

    def _refresh_timecode(self):
        self._seek.blockSignals(True)
        self._seek.setValue(self._current_frame)
        self._seek.blockSignals(False)
        ms       = int(self._current_frame * 1000 / self._fps)
        total_ms = int(self._total_frames * 1000 / self._fps)
        self._time_lbl.setText(f"{_ms_to_hms(ms)} / {_ms_to_hms(total_ms)}")

    def _start_playback(self):
        self._playing = True
        self._play_btn.setText("⏸")
        self._timer.start()

    def _stop_playback(self):
        self._playing = False
        self._play_btn.setText("▶")
        self._timer.stop()

    def _toggle_play(self):
        if self._cap is None:
            return
        if self._playing:
            self._stop_playback()
        else:
            if self._current_frame >= self._total_frames - 1:
                self._seek_to(0)
            self._start_playback()

    # ------------------------------------------------------------------ #
    #  Slider interaction                                                  #
    # ------------------------------------------------------------------ #

    def _on_slider_pressed(self):
        self._slider_dragging = True
        self._timer.stop()

    def _on_slider_released(self):
        self._slider_dragging = False
        self._seek_to(self._seek.value())
        if self._playing:
            self._timer.start()

    # ------------------------------------------------------------------ #
    #  Key / close                                                         #
    # ------------------------------------------------------------------ #

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Space and self._cap is not None:
            self._toggle_play()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self._timer.stop() if hasattr(self, "_timer") else None
        if self._cap and self._cap.isOpened():
            self._cap.release()
        super().closeEvent(event)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv + ["-platform", "windows:darkmode=1"])
    app.setStyle("Fusion")
    test = sys.argv[1] if len(sys.argv) > 1 else ""
    if test:
        dlg = VideoPlayerDialog(test)
        dlg.show()
        sys.exit(app.exec_())
    else:
        print("Usage: video_player.py <video_path>")
        sys.exit(1)
