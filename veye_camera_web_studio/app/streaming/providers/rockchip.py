"""Rockchip (RK3588) provider: videoconvert is fine for MJPEG (RGA/KMPP optional)."""
from __future__ import annotations

from typing import Dict

from .base import StreamProvider


class RockchipProvider(StreamProvider):
    platform = "rockchip"
    ENCODERS: Dict[str, Dict[str, object]] = {
        "jpeg": {"element": "jpegenc", "label": "MJPEG", "hardware": False},
        "h264": {"element": "mpph264enc", "label": "H.264 (RKMPP)", "hardware": True},
    }
