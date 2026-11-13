"""Jetson provider: ``nvvidconv``/``videoconvert`` into I420, then a JPEG encoder.

Unlike Rockchip's ``mppjpegenc`` (which eats the capture node's UYVY dmabuf
directly), NVIDIA's ``nvjpegenc`` only accepts I420/YV12/GRAY8 (sysmem) or
I420/NV12 (NVMM) - never raw UYVY.  So on Jetson the color/scale convert stage is
*always* required, whether we end up encoding on the GPU (``nvjpegenc``) or on the
CPU (``jpegenc``); only the final encoder element changes.  That is why this
provider pins ``needs_cpu_convert()`` to True and merely swaps the encoder.
"""
from __future__ import annotations

from typing import Dict, List

from .base import StreamProvider
from ..profile import StreamProfile


class JetsonProvider(StreamProvider):
    platform = "jetson"
    ENCODERS: Dict[str, Dict[str, object]] = {
        "jpeg": {"element": "jpegenc", "label": "MJPEG (CPU)", "hardware": False},
        "jpeg_hw": {"element": "nvjpegenc", "label": "MJPEG (NVJPEG)", "hardware": True},
        "h264": {"element": "nvv4l2h264enc", "label": "H.264 (NVENC)", "hardware": True},
    }
    # NVJPEG (GPU) first, portable CPU encoder second.  ``nvjpegenc`` is only
    # selected when it is actually installed; otherwise ``jpegenc`` wins, so the
    # behaviour is unchanged on boards without the L4T nvjpeg plugin.
    JPEG_ENCODER_PREFERENCE = ("nvjpegenc", "jpegenc")
    # The convert stage always yields I420, which nvjpegenc accepts, so both the
    # GX (UYVY) and MV (GRAY8) capture formats are eligible for the hardware path.
    HW_JPEG_INPUT_FORMATS = ("UYVY", "GRAY8")

    def needs_cpu_convert(self, profile: StreamProfile) -> bool:
        # nvjpegenc does not consume raw UYVY/GRAY8 from the capture node, so a
        # convert to I420 is required for the hardware path too - unlike the base
        # class, where picking a hardware encoder skips the converter entirely.
        return True

    def capture_to_encoder_tokens(self, profile: StreamProfile) -> List[str]:
        # nvvidconv moves the VI (often NVMM/MPLANE) buffer into I420 and does the
        # color conversion / scaling on the VIC, leaving only the JPEG compression
        # to nvjpegenc (GPU) or jpegenc (CPU).  Fall back to videoconvert when the
        # L4T gstreamer plugins are unavailable.
        #
        # MV/RAW outputs GRAY8, which nvvidconv does not accept as input, so the
        # grayscale path always uses videoconvert (needs the capture buffer to be
        # CPU-mappable; verify on real Jetson hardware if NVMM is involved).
        if (profile.series or "gx").lower() == "mv":
            return ["videoconvert", "!", "video/x-raw,format=I420"]
        conv = "nvvidconv" if self._has_element("nvvidconv") else "videoconvert"
        return [conv, "!", "video/x-raw,format=I420"]

    def hw_jpeg_extra_tokens(self, profile: StreamProfile, element: str, quality: int) -> List[str]:
        """Constant-quality settings for ``nvjpegenc``.

        ``quality`` is the 0-100 baseline-JPEG quality and maps directly to the
        CPU ``jpegenc`` value, so switching encoders does not change what the
        quality slider means.  nvjpegenc emits a full standalone JFIF frame per
        buffer, so ``multipartmux`` viewers that join mid-stream still decode every
        frame (no separate header needed).
        """
        if element != "nvjpegenc":
            return []
        q = max(1, min(100, int(quality)))
        return [f"quality={q}"]
