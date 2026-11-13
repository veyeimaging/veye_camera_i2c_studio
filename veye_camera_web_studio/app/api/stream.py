"""Live-stream API routes (GX series / UYVY only).

Exposes the StreamService lifecycle over HTTP and serves the MJPEG byte stream
that the browser's ``<img>`` renders directly:

  GET  /api/stream/capabilities   platform preview + encoder/transport support
  POST /api/stream/configure      Stage-0 camera configuration (dry_run capable)
  POST /api/stream/start          configure + launch gst pipeline -> stream_id
  POST /api/stream/{id}/stop      terminate pipeline, release device
  GET  /api/stream/status         all active streams (+ device owners)
  GET  /api/stream/{id}/status    one active stream
  GET  /api/stream/{id}/mjpeg     multipart/x-mixed-replace live view
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.stream_service import stream_service
from app.streaming.profile import CameraTopology, CaptureFormat
from app.streaming.util import ValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stream", tags=["stream"])

# Live preview supports the GX series (UYVY) and MV/RAW series (8-bit GREY).
SUPPORTED_SERIES = ("gx", "mv")


class StreamRequest(BaseModel):
    """Body for /configure and /start.

    ``camera`` is the probe result for the selected device and carries the
    topology fields (video_node, media_node, video_subdev/video_subnode,
    media_entity_name, i2c_bus, i2c_addr).
    """
    platform: str = "unknown"
    camera: Dict[str, Any] = Field(default_factory=dict)
    series: str = "gx"
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    roi_x: int = 0
    roi_y: int = 0
    # GX video-mode capability: 1=ROI, 2=Preset.  None -> auto-detect via I2C.
    cap_mode: Optional[int] = None
    preset_mode: Optional[int] = None
    transport: str = "mjpeg"
    jpeg_quality: int = 85
    skip_configure: bool = False
    dry_run: bool = False


def _build(req: StreamRequest):
    """Validate series and convert the body into (topology, fmt)."""
    series = (req.series or req.camera.get("series") or "gx").lower()
    if series not in SUPPORTED_SERIES:
        raise HTTPException(
            status_code=400,
            detail="Live preview currently supports only the GX (UYVY) and "
                   "MV/RAW (GREY) series.",
        )
    if not req.camera.get("video_node"):
        raise HTTPException(status_code=400, detail="camera.video_node is required")
    topo = CameraTopology.from_dict(req.camera)
    fmt = CaptureFormat(
        series=series,
        width=req.width,
        height=req.height,
        fps=req.fps,
        roi_x=req.roi_x,
        roi_y=req.roi_y,
        cap_mode=req.cap_mode,
        preset_mode=req.preset_mode,
    )
    return topo, fmt


@router.get("/capabilities")
def get_capabilities(
    platform: str = Query("unknown"),
    video_node: str = Query(""),
    i2c_bus: Optional[int] = Query(None),
    i2c_addr: str = Query("0x3b"),
    series: str = Query("gx"),
) -> Dict[str, Any]:
    """Previewable formats + platform encode/transport support for the UI."""
    return stream_service.get_capabilities(platform, video_node, i2c_bus, i2c_addr, series)


@router.post("/configure")
def configure(req: StreamRequest) -> Dict[str, Any]:
    """Run Stage-0 (host pipeline) + I2C camera configuration.

    Use ``dry_run=true`` to preview the exact command plan without touching the
    camera.  Non-dry runs are also executed automatically by ``/start``.
    """
    topo, fmt = _build(req)
    try:
        return stream_service.configure(req.platform, topo, fmt, dry_run=req.dry_run)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("configure failed")
        raise HTTPException(status_code=500, detail=f"configure error: {e}")


@router.post("/start")
def start(req: StreamRequest) -> Dict[str, Any]:
    """Configure (unless skipped) and launch the capture pipeline."""
    topo, fmt = _build(req)
    try:
        result = stream_service.start(
            platform=req.platform,
            topo=topo,
            fmt=fmt,
            transport=req.transport,
            jpeg_quality=req.jpeg_quality,
            skip_configure=req.skip_configure,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("start failed")
        raise HTTPException(status_code=500, detail=f"start error: {e}")

    if not result.get("ok"):
        status = 409 if result.get("busy") else 400
        raise HTTPException(status_code=status, detail=result.get("error") or "start failed")
    return result


@router.post("/{stream_id}/stop")
def stop(stream_id: str) -> Dict[str, Any]:
    """Stop a running stream and release its device node."""
    return stream_service.stop(stream_id)


@router.get("/status")
def status() -> Dict[str, Any]:
    """List all active streams and current device ownership."""
    return stream_service.status()


@router.get("/{stream_id}/status")
def stream_status(stream_id: str) -> Dict[str, Any]:
    data = stream_service.status(stream_id)
    if not data["streams"]:
        raise HTTPException(status_code=404, detail=f"Unknown stream: {stream_id}")
    return data["streams"][0]


@router.get("/{stream_id}/mjpeg")
async def mjpeg(stream_id: str):
    """Serve the live MJPEG multipart stream for an <img> tag."""
    active = stream_service.get(stream_id)
    if active is None:
        raise HTTPException(status_code=404, detail=f"Unknown stream: {stream_id}")
    media_type = active.media_type or "multipart/x-mixed-replace; boundary=frame"
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        stream_service.stream_chunks(stream_id),
        media_type=media_type,
        headers=headers,
    )
