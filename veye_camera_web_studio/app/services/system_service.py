"""System information service - collects OS, kernel, platform details."""
import platform
import subprocess
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SystemService:
    """Collects system-level information."""

    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Return OS, kernel, architecture, hostname info."""
        info = {
            "hostname": platform.node(),
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "platform": SystemService._detect_platform(),
        }
        # Try to get more detailed OS info from /etc/os-release
        try:
            with open("/etc/os-release", "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("PRETTY_NAME="):
                        info["os_pretty_name"] = line.split("=", 1)[1].strip('"')
                        break
        except (FileNotFoundError, PermissionError):
            pass
        return info

    @staticmethod
    def _detect_platform() -> str:
        """Detect if running on Jetson, Raspberry Pi, or RK3588."""
        # Check for Jetson
        try:
            with open("/proc/device-tree/compatible", "r") as f:
                compat = f.read().lower()
                if "nvidia" in compat or "jetson" in compat:
                    return "jetson"
                if "rockchip" in compat or "rk3588" in compat or "rk3399" in compat:
                    return "rockchip"
        except (FileNotFoundError, PermissionError):
            pass

        # Check for Raspberry Pi
        try:
            with open("/proc/cpuinfo", "r") as f:
                content = f.read().lower()
                if "raspberry" in content or "bcm2" in content:
                    # Detect Pi 5 vs older
                    if "bcm2712" in content:
                        return "rpi5"
                    return "rpi"
        except (FileNotFoundError, PermissionError):
            pass

        # Check via device-tree model
        try:
            with open("/proc/device-tree/model", "r") as f:
                model = f.read().lower()
                if "jetson" in model:
                    return "jetson"
                if "raspberry" in model:
                    if "5" in model:
                        return "rpi5"
                    return "rpi"
                if "rockchip" in model or "rk3588" in model:
                    return "rockchip"
        except (FileNotFoundError, PermissionError):
            pass

        return "unknown"

    @staticmethod
    def get_media_ctl_info() -> Optional[Dict[str, Any]]:
        """Check if media-ctl is available and return basic info."""
        try:
            result = subprocess.run(
                ["media-ctl", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return {"available": True, "version": result.stdout.strip()}
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return {"available": False, "version": None}

    @staticmethod
    def get_i2c_devices() -> list:
        """List available I2C device nodes."""
        import glob
        devices = []
        for path in sorted(glob.glob("/dev/i2c-*")):
            bus_num = path.split("-")[-1]
            devices.append({"path": path, "bus": bus_num})
        return devices

    @staticmethod
    def get_video_devices() -> list:
        """List available video device nodes."""
        import glob
        devices = []
        for path in sorted(glob.glob("/dev/video*")):
            devices.append({"path": path})
        return devices
