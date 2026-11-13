"""MJPEG-over-HTTP transport (v1 default).

Pipeline tail:  ``... ! <jpeg encoder> ! multipartmux ! filesink location=/dev/stdout``
The encoder element comes from the platform provider (hardware ``mppjpegenc`` on
Rockchip, ``jpegenc`` elsewhere); this transport only frames the JPEG bitstream as
multipart and pipes it to a Starlette ``StreamingResponse`` with
``multipart/x-mixed-replace`` so a plain ``<img src=...>`` renders live.
"""
from __future__ import annotations

from typing import List

from .base import StreamTransport
from ..profile import StreamProfile

BOUNDARY = "frame"


class MjpegTransport(StreamTransport):
    name = "mjpeg"
    media_type = f"multipart/x-mixed-replace; boundary={BOUNDARY}"

    def sink_tokens(self, profile: StreamProfile, provider=None) -> List[str]:
        if provider is not None:
            encoder = provider.jpeg_encoder_tokens(profile)
        else:
            quality = max(1, min(100, int(profile.jpeg_quality)))
            encoder = ["jpegenc", f"quality={quality}"]
        return encoder + [
            "!", "multipartmux", f"boundary={BOUNDARY}",
            "!", "filesink", "location=/dev/stdout",
        ]

    def playback_url(self, stream_id: str) -> str:
        return f"/api/stream/{stream_id}/mjpeg"
