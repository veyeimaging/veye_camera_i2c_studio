"""Stage 2 transport registry."""
from __future__ import annotations

from .base import StreamTransport
from .mjpeg import MjpegTransport

_REGISTRY = {
    "mjpeg": MjpegTransport,
    # "h264_ws": H264WsTransport,   # v2
}


def available_transports() -> list:
    return list(_REGISTRY.keys())


def get_transport(name: str) -> StreamTransport:
    cls = _REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown transport: {name}. Available: {list(_REGISTRY)}")
    return cls()


__all__ = ["StreamTransport", "MjpegTransport", "get_transport", "available_transports"]
