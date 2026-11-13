"""Jetson configurator (GX UYVY + MV GREY).

Same video-node path as Raspberry Pi, plus a Jetson-specific requirement: the
VI prefers strides aligned to 256, so we round width up and program the
``preferred_stride`` control -- applied for both series, matching veye_viewer
onSetRoiAndFps(Jetson).
"""
from __future__ import annotations

from typing import List

from .base import StreamConfigurator
from ..profile import CameraTopology, CaptureFormat
from ..util import align_up


class JetsonConfigurator(StreamConfigurator):
    platform = "jetson"

    def host_commands(self, topo: CameraTopology, fmt: CaptureFormat) -> List[List[str]]:
        cmds: List[List[str]] = []
        if self.sets_roi(fmt):
            cmds += self._roi_cmds(topo.video_node, fmt)
        cmds.append([
            "v4l2-ctl", "-d", topo.video_node, "--set-fmt-video",
            f"width={fmt.width},height={fmt.height},pixelformat={self.v4l2_pixfmt(fmt)}",
        ])
        aligned = align_up(int(fmt.width), 256)
        cmds.append([
            "v4l2-ctl", "-d", topo.video_node, "--set-ctrl", f"preferred_stride={aligned}",
        ])
        return cmds
