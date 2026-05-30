"""
core/probe.py
─────────────
Thin wrapper around ffprobe for extracting technical metadata from video files.

Any part of the app that needs video information imports this module
rather than calling ffprobe directly.  That keeps all subprocess /
JSON-parsing logic in one place and makes the rest of the codebase
easy to test and change.

Usage
-----
    from core.probe import probe_video, fmt_duration, fmt_resolution

    info = probe_video("/path/to/shot.mp4")
    # {"width": 1920, "height": 1080, "fps": 23.976, "duration": 125.4,
    #  "nb_frames": 3010, "codec": "h264", "audio_codec": "aac",
    #  "bit_rate": 8500000}

    print(fmt_duration(info.get("duration", 0)))   # "00:02:05"
    print(fmt_resolution(info))                    # "1920 × 1080"
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


# ── ffprobe discovery ─────────────────────────────────────────────────────── #

def _ffprobe_exe() -> str:
    """Return the path to the ffprobe executable, or '' if not found.

    Resolution order:
      1. PATH  (shutil.which)  — covers Homebrew, apt, conda, winget, etc.
      2. Same directory as ffmpeg — they always ship together, so if the
         user has a non-PATH ffmpeg install this still works.
    """
    found = shutil.which("ffprobe")
    if found:
        return found

    # Derive from the sibling ffmpeg path detected at startup
    from core import constants          # imported here to avoid circular import
    if constants.FFMPEG_PATH:
        exe      = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
        sibling  = Path(constants.FFMPEG_PATH).parent / exe
        if sibling.is_file():
            return str(sibling)

    return ""


# ── Core probe function ───────────────────────────────────────────────────── #

def probe_video(path: str) -> dict:
    """Run ffprobe on *path* and return a dict of technical metadata.

    Returned keys (all optional — only present when ffprobe can read them):

        width       int     frame width in pixels
        height      int     frame height in pixels
        fps         float   frames per second  (e.g. 23.976)
        duration    float   total duration in seconds
        nb_frames   int     total frame count
        codec       str     video codec name   (e.g. "h264", "prores")
        audio_codec str     first audio stream codec (e.g. "aac", "pcm_s24le")
        bit_rate    int     container bit rate in bits per second

    Always returns a plain ``dict`` — returns ``{}`` when ffprobe is not
    installed, the file is unreadable, or any other error occurs.
    Callers should never crash regardless of what this returns.
    """
    exe = _ffprobe_exe()
    if not exe:
        return {}

    try:
        result = subprocess.run(
            [
                exe,
                "-v",            "quiet",
                "-print_format", "json",
                "-show_streams",
                "-show_format",
                path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        data = json.loads(result.stdout)
    except Exception:
        return {}

    info: dict = {}
    fmt = data.get("format", {})

    # ── Container-level fields ────────────────────────────────────────────
    try:
        info["duration"] = float(fmt["duration"])
    except (KeyError, ValueError, TypeError):
        pass

    try:
        info["bit_rate"] = int(fmt["bit_rate"])
    except (KeyError, ValueError, TypeError):
        pass

    # ── Per-stream fields ─────────────────────────────────────────────────
    for stream in data.get("streams", []):
        codec_type = stream.get("codec_type")

        if codec_type == "video" and "codec" not in info:
            # Video codec name
            codec_name = stream.get("codec_name")
            if codec_name:
                info["codec"] = codec_name

            # Resolution
            try:
                info["width"]  = int(stream["width"])
                info["height"] = int(stream["height"])
            except (KeyError, ValueError, TypeError):
                pass

            # FPS — stored as a fraction string e.g. "24000/1001" or "30/1"
            for key in ("r_frame_rate", "avg_frame_rate"):
                raw = stream.get(key, "")
                if raw and raw != "0/0":
                    try:
                        info["fps"] = round(float(Fraction(raw)), 3)
                        break
                    except (ValueError, ZeroDivisionError):
                        pass

            # Frame count — may be "N/A" for some formats
            raw_nb = stream.get("nb_frames", "")
            if raw_nb and raw_nb != "N/A":
                try:
                    info["nb_frames"] = int(raw_nb)
                except ValueError:
                    pass

            # Stream-level duration fallback (container duration preferred)
            if "duration" not in info:
                try:
                    info["duration"] = float(stream["duration"])
                except (KeyError, ValueError, TypeError):
                    pass

        elif codec_type == "audio" and "audio_codec" not in info:
            codec_name = stream.get("codec_name")
            if codec_name:
                info["audio_codec"] = codec_name

    return info


# ── Display formatters ────────────────────────────────────────────────────── #

def fmt_duration(seconds: float) -> str:
    """Format *seconds* as ``HH:MM:SS``.

    Example: ``125.4  →  "00:02:05"``
    """
    total_s      = int(seconds)
    mins, s      = divmod(total_s, 60)
    hrs,  m      = divmod(mins, 60)
    return f"{hrs:02d}:{m:02d}:{s:02d}"


def fmt_resolution(info: dict) -> str:
    """Return a ``W × H`` string from a probe dict, or ``''`` if missing.

    Example: ``{"width": 1920, "height": 1080}  →  "1920 × 1080"``
    """
    w = info.get("width")
    h = info.get("height")
    if w and h:
        return f"{w} × {h}"
    return ""


def fmt_fps(fps: float) -> str:
    """Format a frames-per-second value for display.

    Common values are shown without trailing zeros:
        24.0     →  "24 fps"
        23.976   →  "23.976 fps"
        29.97    →  "29.97 fps"
    """
    return f"{fps:g} fps"


def fmt_bitrate(bps: int) -> str:
    """Format a bit-rate value (bits per second) for display.

    Examples:
        500_000      →  "500 Kbps"
        8_500_000    →  "8.5 Mbps"
        120_000_000  →  "120 Mbps"
    """
    if bps >= 1_000_000:
        val = bps / 1_000_000
        return f"{val:g} Mbps"
    if bps >= 1_000:
        val = bps / 1_000
        return f"{val:g} Kbps"
    return f"{bps} bps"
