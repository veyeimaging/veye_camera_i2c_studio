"""Stage 1 - platform capture + encode providers.

A provider contributes the *front* of the GStreamer pipeline: it turns the raw
frames coming out of ``v4l2src`` into a format the encoder expects (I420 for the
software MJPEG path), and it resolves *which* encoder element should do the JPEG
compression on this platform.  Hardware JPEG encoders are opted in per platform by
listing them in ``JPEG_ENCODER_PREFERENCE``; the pipeline then skips the CPU
color-convert stage, because those encoders eat the capture buffer directly.
It also advertises which encoders this platform supports so the UI / StreamService
can pick a sane default and hide unavailable options.
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Dict, List

from ..profile import StreamProfile


class StreamProvider:
    """Base provider (shared by rpi / rockchip).  Jetson overrides the converter.

    Platform key <-> SystemService._detect_platform(): jetson / rockchip / rpi5 / rpi
    """
    platform: str = "generic"
    # element name -> {label, hardware}
    ENCODERS: Dict[str, Dict[str, object]] = {
        "jpeg": {"element": "jpegenc", "label": "MJPEG", "hardware": False},
    }
    # MJPEG encoder candidates, hardware first.  The first one that is actually
    # installed wins; ``jpegenc`` is the portable CPU fallback and is always used
    # when nothing else matches, so listing an absent element is harmless.
    JPEG_ENCODER_PREFERENCE: tuple = ("jpegenc",)
    # Capture formats a hardware encoder above accepts without a CPU convert.
    # Empty (the default) means "no hardware JPEG path on this platform".
    HW_JPEG_INPUT_FORMATS: tuple = ()
    # gst-inspect is ~50ms per call and pipeline builds happen per stream: cache.
    _ELEMENT_CACHE: Dict[str, bool] = {}

    def __init__(self, platform: str | None = None) -> None:
        # Allow one class to serve several platform keys (e.g. rpi + rpi5).
        if platform:
            self.platform = platform

    # ---- pipeline contribution -------------------------------------------
    def io_mode(self, profile: StreamProfile) -> str:
        """v4l2src io-mode.  GStreamer numbers these 0 auto / 1 read / 2 mmap /
        3 userptr / 4 dmabuf, so ``4`` is dmabuf (zero-copy), not mmap.  It works on
        SPLANE/MPLANE capture nodes including Rockchip rkcif; ``2`` (mmap) is the
        fallback for drivers that refuse DMABUF export."""
        return "4"

    def jpeg_encoder(self, profile: StreamProfile) -> str:
        """Element that will do the JPEG encoding for this stream.

        ``profile.encoder`` selects the policy: ``"jpeg"`` (default) means "auto -
        hardware when this platform has a usable one", ``"jpeg_sw"`` forces the
        portable ``jpegenc``.  A hardware encoder is only chosen when it exists on
        the board *and* the native capture format is one it accepts, so unusual
        formats (e.g. MV/GRAY8) keep working on the CPU path.
        """
        if (profile.encoder or "jpeg").lower() == "jpeg_sw":
            return "jpegenc"
        if profile.input_format in self.HW_JPEG_INPUT_FORMATS:
            for element in self.JPEG_ENCODER_PREFERENCE:
                if element != "jpegenc" and self.has_element(element):
                    return element
        return "jpegenc"

    def needs_cpu_convert(self, profile: StreamProfile) -> bool:
        """True when frames must be turned into sysmem I420 before encoding."""
        return self.jpeg_encoder(profile) == "jpegenc"

    def capture_to_encoder_tokens(self, profile: StreamProfile) -> List[str]:
        """Tokens that convert v4l2src output -> ``video/x-raw,format=I420``.

        The returned list is inserted *after* ``! <input_caps> !`` and *before*
        the transport's encoder stage.  Default path uses ``videoconvert``; the
        hardware JPEG path needs none at all, hence an empty list (the pipeline
        builder then omits the extra ``!`` separator).
        """
        if not self.needs_cpu_convert(profile):
            return []
        return ["videoconvert", "!", "video/x-raw,format=I420"]

    def jpeg_encoder_tokens(self, profile: StreamProfile) -> List[str]:
        """Encoder element + its properties, as pipeline tokens.

        Kept here (not in the transport) because "which encoder" is a platform
        capability, while "how to mux/deliver it" is the transport's business.
        """
        element = self.jpeg_encoder(profile)
        quality = max(1, min(100, int(profile.jpeg_quality)))
        if element == "jpegenc":
            return [element, f"quality={quality}"]
        return [element] + self.hw_jpeg_extra_tokens(profile, element, quality)

    def hw_jpeg_extra_tokens(self, profile: StreamProfile, element: str, quality: int) -> List[str]:
        """Per-encoder properties for hardware JPEG paths (override in platform)."""
        return []

    # ---- capability reporting --------------------------------------------
    @classmethod
    def has_element(cls, element: str) -> bool:
        """Cached ``gst-inspect-1.0`` probe (also used by capabilities())."""
        cached = cls._ELEMENT_CACHE.get(element)
        if cached is not None:
            return cached
        found = cls._has_element_uncached(element)
        cls._ELEMENT_CACHE[element] = found
        return found

    @staticmethod
    def _has_element_uncached(element: str) -> bool:
        if shutil.which("gst-inspect-1.0") is None:
            # No GStreamer tooling -> assume base plugin set present for jpeg.
            return element in ("videoconvert", "jpegenc", "multipartmux", "v4l2src", "filesink")
        try:
            r = subprocess.run(["gst-inspect-1.0", element],
                               capture_output=True, text=True, timeout=5)
            return r.returncode == 0
        except Exception:
            return False

    # Backwards-compatible name used by platform subclasses / older callers.
    @staticmethod
    def _has_element(element: str) -> bool:
        return StreamProvider.has_element(element)

    def capabilities(self) -> Dict[str, object]:
        encoders = {}
        for name, meta in self.ENCODERS.items():
            encoders[name] = {
                "element": meta["element"],
                "label": meta["label"],
                "hardware": bool(meta.get("hardware", False)),
                "available": self.has_element(str(meta["element"])),
            }
        resolved = self.jpeg_encoder(StreamProfile(stream_id="", platform=self.platform))
        return {
            "platform": self.platform,
            "encoders": encoders,
            # What an auto ("jpeg") request actually resolves to on this board.
            "jpeg_encoder_auto": resolved,
            "jpeg_encoder_hardware": resolved != "jpegenc",
            "transports": ["mjpeg"],   # v2 adds "h264_ws"
        }
