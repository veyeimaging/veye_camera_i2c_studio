"""Stage 2 - protocol transports.

A transport contributes the *tail* of the GStreamer pipeline (the encoder +
muxer + sink) and declares how the produced bytes reach the browser.  v1 ships
MJPEG-over-HTTP; later versions can add H.264/MSE and WebRTC behind this same
interface without touching providers or the service.
"""
from __future__ import annotations

from typing import List

from ..profile import StreamProfile


class StreamTransport:
    name: str = "base"
    # HTTP media type for the delivery endpoint (MJPEG uses multipart replace).
    media_type: str = "application/octet-stream"

    def sink_tokens(self, profile: StreamProfile) -> List[str]:
        """Tokens appended after the provider's ``...video/x-raw,format=I420``.

        Must end with ``filesink location=/dev/stdout`` so StreamService can read
        the multiplexed byte stream from the subprocess stdout.
        """
        raise NotImplementedError

    def playback_url(self, stream_id: str) -> str:
        raise NotImplementedError
