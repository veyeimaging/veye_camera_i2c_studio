"""Stage 1 - platform capture + encode providers.

A provider contributes the *front* of the GStreamer pipeline: it turns the raw
frames coming out of ``v4l2src`` into a format the transport's encoder expects
(I420 for MJPEG).  It also advertises which encoders this platform supports so
the UI / StreamService can pick a sane default and hide unavailable options.
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Dict, List

from ..profile import StreamProfile


class StreamProvider:
    """Base provider (shared by rpi / rockchip).  Jetson overrides the converter.

    Platform key <-> SystemService._detect_platform(): jetson / rockchip / rpi5 / rpi
    """
    platform: str = "generic"
    # element name -> {label, hardware}
    ENCODERS: Dict[str, Dict[str, object]] = {
        "jpeg": {"element": "jpegenc", "label": "MJPEG", "hardware": False},
    }

    def __init__(self, platform: str | None = None) -> None:
        # Allow one class to serve several platform keys (e.g. rpi + rpi5).
        if platform:
            self.platform = platform

    # ---- pipeline contribution -------------------------------------------
    def io_mode(self, profile: StreamProfile) -> str:
        """v4l2src io-mode.  4 = mmap (default, works for SPLANE/MPLANE)."""
        return "4"

    def capture_to_encoder_tokens(self, profile: StreamProfile) -> List[str]:
        """Tokens that convert v4l2src output -> ``video/x-raw,format=I420``.

        The returned list is inserted *after* ``! <input_caps> !`` and *before*
        the transport's encoder stage.  Default path uses ``videoconvert``.
        """
        return ["videoconvert", "!", "video/x-raw,format=I420"]

    # ---- capability reporting --------------------------------------------
    @staticmethod
    def _has_element(element: str) -> bool:
        if shutil.which("gst-inspect-1.0") is None:
            # No GStreamer tooling -> assume base plugin set present for jpeg.
            return element in ("videoconvert", "jpegenc", "multipartmux", "v4l2src", "filesink")
        try:
            r = subprocess.run(["gst-inspect-1.0", element],
                               capture_output=True, text=True, timeout=5)
            return r.returncode == 0
        except Exception:
            return False

    def capabilities(self) -> Dict[str, object]:
        encoders = {}
        for name, meta in self.ENCODERS.items():
            encoders[name] = {
                "element": meta["element"],
                "label": meta["label"],
                "hardware": bool(meta.get("hardware", False)),
                "available": self._has_element(str(meta["element"])),
            }
        return {
            "platform": self.platform,
            "encoders": encoders,
            "transports": ["mjpeg"],   # v2 adds "h264_ws"
        }
