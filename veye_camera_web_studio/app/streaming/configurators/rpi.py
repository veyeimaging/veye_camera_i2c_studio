"""Raspberry Pi (Pi 4 and older) configurator (GX UYVY + MV GREY).

These boards expose a single V4L2 device where both the ROI controls and the
capture format are set directly on the video node (no separate media-ctl entity
negotiation is required).  Matches veye_viewer onSetRoiAndFps(RaspberryPi).
"""
from __future__ import annotations

from typing import List

from .base import StreamConfigurator
from ..profile import CameraTopology, CaptureFormat


class RpiConfigurator(StreamConfigurator):
    platform = "rpi"

    def host_commands(self, topo: CameraTopology, fmt: CaptureFormat) -> List[List[str]]:
        cmds: List[List[str]] = []
        if self.sets_roi(fmt):
            cmds += self._roi_cmds(topo.video_node, fmt)
        cmds.append([
            "v4l2-ctl", "-d", topo.video_node, "--set-fmt-video",
            f"width={fmt.width},height={fmt.height},pixelformat={self.v4l2_pixfmt(fmt)}",
        ])
        return cmds
