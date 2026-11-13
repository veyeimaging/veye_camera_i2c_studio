"""Rockchip (RK3588) configurator (GX UYVY + MV GREY).

Mirrors veye_viewer onSetRoiAndFps(Rockchip): ROI offsets go to the *subdev*
node; resolution + fps are negotiated on the sensor entity via media-ctl using
the series media-bus code (GX UYVY8_2X8, MV Y8_1X8).
"""
from __future__ import annotations

from typing import List

from .base import StreamConfigurator
from ..profile import CameraTopology, CaptureFormat


class RockchipConfigurator(StreamConfigurator):
    platform = "rockchip"

    def host_commands(self, topo: CameraTopology, fmt: CaptureFormat) -> List[List[str]]:
        cmds: List[List[str]] = []
        if self.sets_roi(fmt):
            cmds += self._roi_cmds(topo.video_subnode, fmt)
        cmds.append([
            "media-ctl", "-d", topo.media_node, "--set-v4l2",
            f'"{topo.media_entity_name}":0[fmt:{self.bus_fmt(fmt)}/{fmt.width}x{fmt.height}@1/{int(fmt.fps)}]',
        ])
        return cmds
