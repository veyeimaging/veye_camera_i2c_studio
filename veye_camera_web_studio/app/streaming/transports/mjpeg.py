"""MJPEG-over-HTTP transport (v1 default).

Pipeline tail:  ``... ! jpegenc ! multipartmux ! filesink location=/dev/stdout``
The multipart byte stream is piped straight to a Starlette ``StreamingResponse``
with ``multipart/x-mixed-replace`` so a plain ``<img src=...>`` renders live.
"""
from __future__ import annotations

from typing import List

from .base import StreamTransport
from ..profile import StreamProfile

BOUNDARY = "frame"


class MjpegTransport(StreamTransport):
    name = "mjpeg"
    media_type = f"multipart/x-mixed-replace; boundary={BOUNDARY}"

    def sink_tokens(self, profile: StreamProfile) -> List[str]:
        quality = max(1, min(100, int(profile.jpeg_quality)))
        return [
            "jpegenc", f"quality={quality}",
            "!", "multipartmux", f"boundary={BOUNDARY}",
            "!", "filesink", "location=/dev/stdout",
        ]

    def playback_url(self, stream_id: str) -> str:
        return f"/api/stream/{stream_id}/mjpeg"
