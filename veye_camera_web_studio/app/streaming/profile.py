"""Data structures shared across the streaming subsystem.

Two logical groups:
  - Topology + capture format: describe *which* camera and *what* picture,
    consumed by Stage 0 (Configurator).
  - StreamProfile: everything needed to build a GStreamer pipeline, consumed by
    Stage 1 (Provider) + Stage 2 (Transport) + StreamService.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class StreamState(str, Enum):
    IDLE = "idle"
    CONFIGURING = "configuring"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


# GStreamer ``v4l2src`` caps format name per series (V4L2 fourcc -> caps string).
#   GX: UYVY color;   MV: 8-bit grayscale (fourcc GREY -> caps GRAY8).
# ``videoconvert`` (gst-plugins-base) turns either into I420 for jpegenc, so no
# extra GStreamer plugin is required for the MV path versus GX.
SERIES_INPUT_FORMAT = {"gx": "UYVY", "mv": "GRAY8"}


def series_input_format(series: str) -> str:
    return SERIES_INPUT_FORMAT.get((series or "gx").lower(), "UYVY")


@dataclass
class CameraTopology:
    """Device topology for one camera, as produced by ProbeService.

    All fields are strings/ints coming straight from the probe result:
      media_node        e.g. /dev/media0
      video_node        e.g. /dev/video0     (frame capture node)
      video_subnode     e.g. /dev/v4l-subdev0  (ROI controls on RK)
      media_entity_name e.g. "gxcam 10-003b"  (media-ctl entity)
      i2c_bus           e.g. 10
      i2c_addr          e.g. 0x3b
    """
    media_node: str
    video_node: str
    video_subnode: str
    media_entity_name: str
    i2c_bus: int
    i2c_addr: str = "0x3b"

    @classmethod
    def from_dict(cls, d: dict) -> "CameraTopology":
        bus_raw = d.get("i2c_bus", 0)
        try:
            bus = int(str(bus_raw))
        except (TypeError, ValueError):
            bus = 0
        return cls(
            media_node=str(d.get("media_node", "")).strip(),
            video_node=str(d.get("video_node", "")).strip(),
            video_subnode=str(d.get("video_subnode", d.get("video_subdev", ""))).strip(),
            media_entity_name=str(d.get("media_entity_name", d.get("entity_name", ""))).strip(),
            i2c_bus=bus,
            i2c_addr=str(d.get("i2c_addr", "0x3b")).strip() or "0x3b",
        )


@dataclass
class CaptureFormat:
    """Target picture + video-mode capability, used by Stage 0.

    Supported series:
      "gx": UYVY color, two flavours distinguished by VideoModeCap;
      "mv": 8-bit grayscale (GREY), always free ROI, no VideoModeCap.

    series:      "gx" or "mv"
    cap_mode:    GX video-mode capability: 1 = ROI mode, 2 = Preset mode (MV: None)
    preset_mode: preset resolution mode index when cap_mode == 2
    """
    series: str
    width: int
    height: int
    fps: float
    roi_x: int = 0
    roi_y: int = 0
    cap_mode: Optional[int] = None
    preset_mode: Optional[int] = None


@dataclass
class StreamProfile:
    """Fully-resolved parameters for one live stream (a single gst-launch run)."""
    stream_id: str
    platform: str
    series: str = "gx"          # "gx" (UYVY) | "mv" (GRAY8)
    video_node: str = ""
    width: int = 1920
    height: int = 1080
    fps: int = 30
    transport: str = "mjpeg"    # "mjpeg" | "h264_ws" (v2)
    # "jpeg"  = auto, i.e. hardware encoder if this platform provides a usable one
    # "jpeg_sw" = force the portable CPU encoder (jpegenc), for A/B and fallbacks
    # "h264"  = reserved for the v2 websocket/MSE transport
    encoder: str = "jpeg"
    # Element actually chosen for the encode, filled in by StreamService.start()
    # from the platform provider ("jpegenc" / "mppjpegenc" / ...).
    encoder_element: str = ""
    jpeg_quality: int = 85
    topology: Optional[CameraTopology] = None
    fmt: Optional[CaptureFormat] = None
    # v4l2 pixel fourcc fed to the pipeline: UYVY (gx) / GRAY8 (mv)
    input_format: str = "UYVY"

    def input_caps(self) -> str:
        """v4l2src output caps string (no spaces -> single argv token).

        Deliberately omits ``framerate``: capture drivers can advertise a narrower
        ENUM_FRAMEINTERVALS range than the sensor actually runs at (Rockchip rkcif
        allows 1-30 fps even for a 1080p60 stream), so putting e.g. ``60/1`` in the
        caps makes VIDIOC_S_FMT reject the format and the pipeline dies immediately
        with ``not-negotiated (-4)``.  Frame rate is owned by Stage 0 only - the I2C
        fps register plus the sensor-pad ``@1/fps`` in media-ctl - matching the
        reference veye_viewer, which never sets timeperframe in S_FMT either.
        """
        return (
            f"video/x-raw,format={self.input_format},"
            f"width={self.width},height={self.height}"
        )
