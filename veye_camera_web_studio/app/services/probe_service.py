"""Camera probe service - detects VEYE cameras on supported platforms."""
import subprocess
import logging
import os
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Base directory for probe scripts (within the project's own tools/)
_BASE = os.path.join(os.path.dirname(__file__), "..", "..")
SCRIPTS_DIR = os.path.join(_BASE, "tools", "probe")
_TOOLS_DIR = os.path.join(_BASE, "tools")
_I2C_VREAD = os.path.join(_TOOLS_DIR, "i2c_vread")

# Platform display names
PLATFORM_NAMES = {
    "jetson": "Nvidia Jetson",
    "rockchip": "Rockchip",
    "rpi5": "Raspberry Pi 5",
    "rpi": "Old Raspberry Pi",
}


class ProbeService:
    """Detects VEYE cameras using platform-specific probe scripts."""

    def __init__(self, platform: str = "jetson"):
        self.platform = platform
        self._probe_script_map = {
            "jetson": "probe_camera_info-jetson.sh",
            "rpi": "probe_camera_info-rpi.sh",
            "rpi5": "probe_camera_info-rpi5.sh",
            "rockchip": "probe_camera_info-rk.sh",
        }

    def probe_cameras(self) -> List[Dict[str, Any]]:
        """Run the platform probe script and return detected cameras."""
        script_name = self._probe_script_map.get(self.platform)
        if not script_name:
            logger.warning(f"No probe script for platform: {self.platform}")
            return []

        script_path = os.path.join(SCRIPTS_DIR, script_name)
        if not os.path.isfile(script_path):
            logger.warning(f"Probe script not found: {script_path}")
            return []

        try:
            result = subprocess.run(
                ["bash", script_path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                logger.error(f"Probe script failed: {result.stderr}")
                return []

            # The probe script outputs to auto_camera_index.json or stdout
            return self._parse_probe_output(result.stdout)
        except subprocess.TimeoutExpired:
            logger.error("Probe script timed out")
            return []
        except Exception as e:
            logger.error(f"Probe error: {e}")
            return []

    def _parse_probe_output(self, stdout: str) -> List[Dict[str, Any]]:
        """Parse probe script output into camera list."""
        cameras = []
        # The script outputs key=value pairs
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

    def probe_from_json(self, json_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load camera info from a pre-generated auto_camera_index.json."""
        if json_path is None:
            # Check tools/probe/ first (where probe scripts write), then config/
            for d in [SCRIPTS_DIR, os.path.join(_BASE, "config")]:
                p = os.path.join(d, "auto_camera_index.json")
                if os.path.isfile(p):
                    json_path = p
                    break
        if json_path is None:
            return []
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.debug(f"No existing camera index JSON: {e}")
        return []

    def get_probe_script_info(self) -> Dict[str, Any]:
        """Return info about the probe script for the current platform."""
        script_name = self._probe_script_map.get(self.platform, "unknown")
        script_path = os.path.join(SCRIPTS_DIR, script_name)
        return {
            "platform": self.platform,
            "script_name": script_name,
            "script_exists": os.path.isfile(script_path),
            "script_path": script_path,
        }

    # ------------------------------------------------------------------
    # Full probe with camera details (sysfs + I2C)
    # ------------------------------------------------------------------
    def probe_full(self) -> Dict[str, Any]:
        """Run probe script, then enrich each camera with sysfs/I2C info.

        Returns:
            {"platform": str, "cameras": [{...}], "count": int}
        """
        # 1. Run probe script
        cameras = self.probe_cameras()
        if not cameras:
            cameras = self.probe_from_json()

        # 2. Enrich each camera
        enriched = []
        for cam in cameras:
            info = dict(cam)  # copy basic fields
            bus = cam.get("i2c_bus", "")
            addr = "0x3b"

            # Read camera_model from sysfs
            info["model"] = self._read_sysfs(bus, "camera_model")
            info["fps"] = self._read_sysfs(bus, "fps")
            info["width"] = self._read_sysfs(bus, "width")
            info["height"] = self._read_sysfs(bus, "height")

            # Read version register (0x0010) → split C/L
            ver_raw = self._i2c_read(bus, addr, "0x0010")
            if ver_raw is not None:
                try:
                    ver_int = int(ver_raw, 16)  # hex string from i2c_vread
                    c_ver = (ver_int >> 16) & 0xFFFF
                    l_ver = ver_int & 0xFFFF
                    info["version_c"] = f"{(c_ver >> 8) & 0xFF}.{c_ver & 0xFF:02x}"
                    info["version_l"] = f"{(l_ver >> 8) & 0xFF}.{l_ver & 0xFF:02x}"
                except (ValueError, TypeError):
                    info["version_c"] = "?"
                    info["version_l"] = "?"
            else:
                info["version_c"] = "?"
                info["version_l"] = "?"

            # Read serial register (0x000C)
            ser_raw = self._i2c_read(bus, addr, "0x000C")
            if ser_raw is not None:
                info["serial"] = f"0x{ser_raw.upper()}"
            else:
                info["serial"] = "?"

            info["i2c_addr"] = addr
            enriched.append(info)

        return {
            "platform": self.platform,
            "platform_name": PLATFORM_NAMES.get(self.platform, self.platform),
            "cameras": enriched,
            "count": len(enriched),
        }

    @staticmethod
    def _read_sysfs(bus: str, attr: str) -> str:
        """Read a sysfs attribute for a VEYE camera on the given I2C bus."""
        if not bus:
            return ""
        path = f"/sys/bus/i2c/devices/i2c-{bus}/{bus}-003b/veye_gxcam/{attr}"
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except (FileNotFoundError, PermissionError, OSError):
            return ""

    @staticmethod
    def _i2c_read(bus: str, addr: str, reg: str) -> Optional[str]:
        """Read a single I2C register using i2c_vread. Returns raw hex string or None."""
        if not bus or not os.path.isfile(_I2C_VREAD):
            return None
        try:
            r = subprocess.run(
                [_I2C_VREAD, str(bus), addr, reg, "0"],
                capture_output=True, text=True, timeout=3,
            )
            if r.returncode == 0:
                # "value XXXXXXXX" may appear in stdout or stderr
                combined = r.stdout + "\n" + r.stderr
                for line in combined.split("\n"):
                    line = line.strip()
                    if line.startswith("value "):
                        return line.split()[1]
        except Exception:
            pass
        return None
