"""Jetson platform adapter - platform-specific operations for NVIDIA Jetson."""
import subprocess
import logging
import os
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

PROBE_SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..",
    "tools", "probe", "probe_camera_info-jetson.sh"
)


class JetsonAdapter:
    """Platform-specific adapter for NVIDIA Jetson (Nano, Xavier, Orin, etc.)."""

    PLATFORM_NAME = "jetson"

    def probe_cameras(self) -> List[Dict[str, Any]]:
        """Detect VEYE cameras on Jetson using media-ctl."""
        script_path = os.path.abspath(PROBE_SCRIPT)
        if not os.path.isfile(script_path):
            logger.warning(f"Jetson probe script not found: {script_path}")
            return self._fallback_probe()

        try:
            result = subprocess.run(
                ["bash", script_path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                logger.error(f"Probe failed: {result.stderr}")
                return self._fallback_probe()

            return self._parse_output(result.stdout)
        except Exception as e:
            logger.error(f"Jetson probe error: {e}")
            return self._fallback_probe()

    def _parse_output(self, stdout: str) -> List[Dict[str, Any]]:
        """Parse probe_camera_info-jetson.sh output."""
        cameras = []
        current = {}
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"')
                current[key] = value
        if current:
            cameras.append(current)
        return cameras

    def _fallback_probe(self) -> List[Dict[str, Any]]:
        """Fallback: try to find cameras by scanning media devices."""
        cameras = []
        try:
            for i in range(4):
                media_path = f"/dev/media{i}"
                if os.path.exists(media_path):
                    result = subprocess.run(
                        ["media-ctl", "-d", media_path, "-p"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0 and "gxcam" in result.stdout.lower():
                        cameras.append({
                            "media_node": media_path,
                            "note": "Detected via fallback scan",
                            "raw_output": result.stdout[:500]
                        })
        except Exception as e:
            logger.error(f"Fallback probe error: {e}")
        return cameras

    def get_default_i2c_bus(self) -> int:
        """Return default I2C bus for Jetson (typically 10, but varies by carrier board)."""
        return 10

    def get_default_i2c_addr(self) -> str:
        """Return default I2C address for VEYE cameras."""
        return "0x3b"

    def get_platform_info(self) -> Dict[str, Any]:
        """Return Jetson-specific platform information."""
        info = {
            "platform": self.PLATFORM_NAME,
            "default_i2c_bus": self.get_default_i2c_bus(),
            "default_i2c_addr": self.get_default_i2c_addr(),
            "probe_script": os.path.abspath(PROBE_SCRIPT),
        }
        # Try to read Jetson-specific info
        try:
            with open("/etc/nv_tegra_release", "r") as f:
                info["tegra_release"] = f.read().strip()
        except FileNotFoundError:
            pass
        try:
            with open("/proc/device-tree/model", "r") as f:
                info["board_model"] = f.read().strip().rstrip("\x00")
        except (FileNotFoundError, PermissionError):
            pass
        return info
