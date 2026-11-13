"""Stage 0 - pre-capture camera configuration (GX and MV series).

VEYE cameras come in two series with different native output formats:

    GX : UYVY color   (v4l2 fourcc ``UYVY`` / media bus ``UYVY8_2X8``)
    MV : 8-bit grayscale (``GREY`` / media bus ``Y8_1X8`` / rpi5 script ``RAW8``)

Before ``v4l2src`` can grab a correct picture the host pipeline (media-ctl /
v4l2-ctl / vendor script) and the sensor (I2C) must be aligned.  GX cameras come
in two flavours, distinguished by the VideoModeCap capability register (read via
``CommandService.detect_video_mode_cap``):

    cap_mode == 1 (ROI mode):     free WxH + ROI offset, set through the host.
    cap_mode == 2 (Preset mode):  pick a preset resolution index (I2C videomode);
                                  no ROI offset is written.

MV/RAW has no VideoModeCap concept: it always programs a free ROI on the host.

The I2C side (``videomode`` / ``fps_write`` / ``fps``) is executed by StreamService
via the existing CommandService; this module only produces the *host-side* argv
commands (media-ctl / v4l2-ctl / config script).  All returned commands are argv
lists (no shell).
"""
from __future__ import annotations

from typing import List

from ..profile import CameraTopology, CaptureFormat

# Native output format per series at each configuration layer.
#   v4l2-ctl --set-fmt-video pixelformat=...
_SERIES_V4L2_FMT = {"gx": "UYVY", "mv": "GREY"}
#   media-ctl --set-v4l2 ...[fmt:<bus code>/...]
_SERIES_BUS_FMT = {"gx": "UYVY8_2X8", "mv": "Y8_1X8"}

# Kept for reference / GX default.
GX_PIXFMT = "UYVY"
MV_PIXFMT = "GREY"


class StreamConfigurator:
    platform: str = "generic"

    def __init__(self, platform: str | None = None) -> None:
        if platform:
            self.platform = platform

    # ---- shared helpers ---------------------------------------------------
    @staticmethod
    def series_of(fmt: CaptureFormat) -> str:
        return (fmt.series or "gx").lower()

    @classmethod
    def v4l2_pixfmt(cls, fmt: CaptureFormat) -> str:
        """v4l2-ctl ``--set-fmt-video`` pixelformat fourcc for this series."""
        return _SERIES_V4L2_FMT.get(cls.series_of(fmt), "UYVY")

    @classmethod
    def bus_fmt(cls, fmt: CaptureFormat) -> str:
        """media-ctl media-bus code for this series."""
        return _SERIES_BUS_FMT.get(cls.series_of(fmt), "UYVY8_2X8")

    @classmethod
    def sets_roi(cls, fmt: CaptureFormat) -> bool:
        """Whether a ROI offset must be programmed on the host.

        MV/RAW always uses ROI; GX only in ROI mode (cap 1, not preset cap 2).
        """
        if cls.series_of(fmt) == "mv":
            return True
        return fmt.cap_mode == 1

    @staticmethod
    def _roi_cmds(node: str, fmt: CaptureFormat) -> List[List[str]]:
        return [
            ["v4l2-ctl", "-d", node, "--set-ctrl", f"roi_x={int(fmt.roi_x)}"],
            ["v4l2-ctl", "-d", node, "--set-ctrl", f"roi_y={int(fmt.roi_y)}"],
        ]

    def host_commands(self, topo: CameraTopology, fmt: CaptureFormat) -> List[List[str]]:
        """Return argv commands to prepare the host pipeline for capture.

        Default (unknown platform): nothing to do -- the caller should treat an
        empty list as "no automatic configuration available for this platform".
        """
        return []
