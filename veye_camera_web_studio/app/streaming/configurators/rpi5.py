"""Raspberry Pi 5 configurator.

Pi 5 uses the rp1-cfe/csi2 pipeline that must be reset and linked before capture,
so we delegate to the vendored ``tools/stream/config_camera-rpi5.sh`` (ported from
veye_viewer).  The script itself performs ``media-ctl -r`` + csi2 link + sensor /
csi2 ``--set-v4l2`` + ``v4l2-ctl --set-fmt-video`` (with rec709 tagging) and, for
gxcam, programs ``roi_x`` / ``roi_y`` on the subdev.
"""
from __future__ import annotations

import os
from typing import List

from .base import StreamConfigurator
from ..profile import CameraTopology, CaptureFormat

_HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.abspath(
    os.path.join(_HERE, "..", "..", "..", "tools", "stream", "config_camera-rpi5.sh")
)


class Rpi5Configurator(StreamConfigurator):
    platform = "rpi5"

    # config_camera-rpi5.sh subcommand + -fmt token per series (matches veye_viewer).
    _SERIES_SCRIPT = {"gx": ("gxcam", "UYVY"), "mv": ("mvcam", "RAW8")}

    def host_commands(self, topo: CameraTopology, fmt: CaptureFormat) -> List[List[str]]:
        sub, fmt_token = self._SERIES_SCRIPT.get(self.series_of(fmt), ("gxcam", "UYVY"))
        # Preset mode (GX cap 2) must not shift the ROI: program offset 0,0.
        roi_x = int(fmt.roi_x) if self.sets_roi(fmt) else 0
        roi_y = int(fmt.roi_y) if self.sets_roi(fmt) else 0
        return [
            [
                "bash", SCRIPT, sub, "-fmt", fmt_token,
                "-x", str(roi_x), "-y", str(roi_y),
                "-w", str(fmt.width), "-h", str(fmt.height),
                "-bus", str(topo.i2c_bus), "-media", topo.media_node,
                "-subdev", topo.video_subnode, "-video", topo.video_node,
            ]
        ]
