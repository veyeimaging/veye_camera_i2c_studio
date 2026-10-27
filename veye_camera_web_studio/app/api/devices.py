"""Device API routes - camera detection and system information."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

from app.services.system_service import SystemService
from app.services.probe_service import ProbeService, PLATFORM_NAMES
from app.adapters.jetson.adapter import JetsonAdapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["devices"])

# Singleton services
_system_service = SystemService()
_jetson_adapter = JetsonAdapter()


@router.get("/system/info")
def get_system_info() -> Dict[str, Any]:
    """Get system information (OS, kernel, platform, etc.)."""
    info = _system_service.get_system_info()
    info["media_ctl"] = _system_service.get_media_ctl_info()
    info["i2c_devices"] = _system_service.get_i2c_devices()
    info["video_devices"] = _system_service.get_video_devices()
    return info


@router.get("/devices/cameras")
def get_cameras() -> Dict[str, Any]:
    """Detect and return connected VEYE cameras."""
    platform = _system_service.get_system_info().get("platform", "unknown")
    probe = ProbeService(platform=platform)

    # First try running the probe script
    cameras = probe.probe_cameras()

    # If no results, try loading from JSON
    if not cameras:
        cameras = probe.probe_from_json()

    return {
        "platform": platform,
        "cameras": cameras,
        "count": len(cameras),
        "probe_script": probe.get_probe_script_info(),
    }


@router.get("/devices/platform")
def get_platform_info() -> Dict[str, Any]:
    """Get platform-specific adapter information."""
    platform = _system_service.get_system_info().get("platform", "unknown")
    if platform == "jetson":
        return _jetson_adapter.get_platform_info()
    return {"platform": platform, "supported": False}


@router.post("/devices/scan")
def scan_devices() -> Dict[str, Any]:
    """Force a fresh device scan."""
    platform = _system_service.get_system_info().get("platform", "unknown")
    probe = ProbeService(platform=platform)
    cameras = probe.probe_cameras()
    return {
        "platform": platform,
        "cameras": cameras,
        "count": len(cameras),
    }


class ProbeRequest(BaseModel):
    platform: str = "jetson"


@router.post("/devices/probe")
def probe_cameras(req: ProbeRequest) -> Dict[str, Any]:
    """Run probe for the given platform and return enriched camera info."""
    platform = req.platform
    if platform not in PLATFORM_NAMES:
        raise HTTPException(400, f"Unknown platform: {platform}")
    probe = ProbeService(platform=platform)
    return probe.probe_full()
