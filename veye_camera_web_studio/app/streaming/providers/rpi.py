"""Raspberry Pi provider (Pi 4 and older, and Pi 5).

Pi boards have no practical hardware H.264 *encoder* (VideoCore on Pi0-4 is
weak, Pi5 dropped it entirely), so MJPEG is the primary path.  H.264 is exposed
only opportunistically (``v4l2h264enc`` on Pi0-4) and is not used by v1.
"""
from __future__ import annotations

from typing import Dict

from .base import StreamProvider


class RpiProvider(StreamProvider):
    platform = "rpi"
    ENCODERS: Dict[str, Dict[str, object]] = {
        "jpeg": {"element": "jpegenc", "label": "MJPEG", "hardware": False},
        "h264": {"element": "v4l2h264enc", "label": "H.264 (VideoCore, Pi4-)", "hardware": True},
    }
