"""Rockchip provider: hardware MJPEG through the MPP JPEG encoder.

The CPU path (``videoconvert ! jpegenc``) tops out around 31 fps at 1080p even on
8-core RK SoCs, because both elements are single-threaded, while the sensor happily
delivers 60 fps.  ``mppjpegenc`` (gst-rockchip / librockchip-mpp) encodes straight
from the capture node's UYVY dmabuf - no color convert, no copy - measured at
~53 fps 1080p on this board, at roughly a third of the CPU-path bitrate.

If the plugin is missing, or the capture format is not one MPP accepts as-is,
``StreamProvider.jpeg_encoder()`` falls back to ``jpegenc`` automatically.
"""
from __future__ import annotations

from typing import Dict, List

from ..profile import StreamProfile
from .base import StreamProvider


class RockchipProvider(StreamProvider):
    platform = "rockchip"
    ENCODERS: Dict[str, Dict[str, object]] = {
        "jpeg": {"element": "jpegenc", "label": "MJPEG (CPU)", "hardware": False},
        "jpeg_hw": {"element": "mppjpegenc", "label": "MJPEG (RKMPP)", "hardware": True},
        "h264": {"element": "mpph264enc", "label": "H.264 (RKMPP)", "hardware": True},
    }
    # RKMPP first, CPU fallback second; only for the formats listed below.
    JPEG_ENCODER_PREFERENCE = ("mppjpegenc", "jpegenc")
    # UYVY (GX) goes in as-is.  MV/GRAY8 is not an MPP JPEG input, so it stays on
    # the software path (videoconvert -> I420 -> jpegenc).
    HW_JPEG_INPUT_FORMATS = ("UYVY",)

    def hw_jpeg_extra_tokens(self, profile: StreamProfile, element: str, quality: int) -> List[str]:
        """Constant-quality settings for ``mppjpegenc``.

        ``rc-mode=fixqp`` stops the rate controller from trading quality away, which
        makes ``q-factor`` behave like jpegenc's ``quality`` (1-99).  ``header-mode``
        is left at its default: MPP still emits a full JFIF/DQT/DHT header per part,
        verified over 337 consecutive mid-stream frames, so a browser that opens the
        MJPEG socket late still decodes every frame.  If a future MPP build changes
        that, set ``header-mode=1`` here and re-run the per-frame marker check.
        """
        if element != "mppjpegenc":
            return []
        q = max(1, min(99, int(quality)))
        return ["rc-mode=fixqp", f"q-factor={q}", "qf-min=1", "qf-max=99"]
