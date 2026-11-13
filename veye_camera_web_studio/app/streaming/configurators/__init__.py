"""Stage 0 configurator registry (keyed by SystemService platform id)."""
from __future__ import annotations

from .base import StreamConfigurator
from .jetson import JetsonConfigurator
from .rockchip import RockchipConfigurator
from .rpi import RpiConfigurator
from .rpi5 import Rpi5Configurator


def get_configurator(platform: str) -> StreamConfigurator:
    if platform == "jetson":
        return JetsonConfigurator()
    if platform == "rockchip":
        return RockchipConfigurator(platform)
    if platform == "rpi5":
        return Rpi5Configurator(platform)
    if platform == "rpi":
        return RpiConfigurator(platform)
    # Unknown platform: base configurator yields no host commands (capture may
    # still work if the pipeline is already configured externally).
    return StreamConfigurator(platform or "generic")


__all__ = [
    "StreamConfigurator",
    "get_configurator",
    "JetsonConfigurator",
    "RockchipConfigurator",
    "RpiConfigurator",
    "Rpi5Configurator",
]
