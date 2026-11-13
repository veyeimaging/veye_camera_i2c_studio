"""Stage 1 provider registry (keyed by SystemService platform id)."""
from __future__ import annotations

from .base import StreamProvider
from .jetson import JetsonProvider
from .rockchip import RockchipProvider
from .rpi import RpiProvider


def get_provider(platform: str) -> StreamProvider:
    """Return a provider instance for the given platform id.

    Unknown platforms fall back to the generic base provider (plain v4l2src +
    videoconvert + jpegenc), which still works wherever GStreamer good plugins
    are installed.
    """
    if platform == "jetson":
        return JetsonProvider()
    if platform == "rockchip":
        return RockchipProvider(platform)
    if platform in ("rpi", "rpi5"):
        return RpiProvider(platform)
    return StreamProvider(platform or "generic")


__all__ = ["StreamProvider", "get_provider", "JetsonProvider", "RockchipProvider", "RpiProvider"]
