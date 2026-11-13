"""Jetson provider: use ``nvvidconv`` for color/scale into sysmem I420."""
from __future__ import annotations

from typing import Dict, List

from .base import StreamProvider
from ..profile import StreamProfile


class JetsonProvider(StreamProvider):
    platform = "jetson"
    ENCODERS: Dict[str, Dict[str, object]] = {
        "jpeg": {"element": "jpegenc", "label": "MJPEG", "hardware": False},
        "h264": {"element": "nvv4l2h264enc", "label": "H.264 (NVENC)", "hardware": True},
    }

    def capture_to_encoder_tokens(self, profile: StreamProfile) -> List[str]:
        # nvvidconv moves the VI (often NVMM/MPLANE) buffer into sysmem I420
        # that jpegenc can consume on the CPU.  Fall back to videoconvert when
        # the L4T gstreamer plugins are unavailable.
        #
        # MV/RAW outputs GRAY8, which nvvidconv does not accept as input, so the
        # grayscale path always uses videoconvert (needs the capture buffer to be
        # CPU-mappable; verify on real Jetson hardware if NVMM is involved).
        if (profile.series or "gx").lower() == "mv":
            return ["videoconvert", "!", "video/x-raw,format=I420"]
        conv = "nvvidconv" if self._has_element("nvvidconv") else "videoconvert"
        return [conv, "!", "video/x-raw,format=I420"]
