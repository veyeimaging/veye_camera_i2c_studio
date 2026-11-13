"""Stream orchestration service (Stage 3).

Ties the four streaming layers together and owns the ``gst-launch-1.0``
subprocess lifecycle:

  Stage 0  Configurator   pre-capture host pipeline (media-ctl / v4l2-ctl / script)
  Stage 0' I2C            GX sensor video-mode + fps (via existing CommandService)
  Stage 1  Provider       platform capture + convert tokens
  Stage 2  Transport      encode + mux + sink tokens (v1: MJPEG over HTTP)

Scope: GX (UYVY) and MV/RAW (8-bit GREY).  GX has two flavours distinguished by
the VideoModeCap capability register:

  cap_mode == 1 (ROI):     free WxH + ROI offset, all programmed host-side;
                           I2C side only writes ``fps_write`` (value = fps*10000).
  cap_mode == 2 (Preset):  pick a preset resolution index via I2C ``videomode``;
                           no ROI offset is written; I2C still writes ``fps_write``.

MV/RAW has no VideoModeCap: it always programs a free ROI host-side (pixel format
GREY / Y8_1X8 / RAW8) and the I2C side writes the MV ``fps`` command (value =
fps*100).  The MJPEG encode path is identical (videoconvert -> I420 -> jpegenc).

Every command is executed as an argv list (``shell=False``) and every dynamic
value coming from the browser / kernel topology is whitelisted first (see
``app.streaming.util``), mirroring veye_viewer's ``isSafeCmdToken`` / ``reInt``.
"""
from __future__ import annotations

import os
import asyncio
import logging
import shutil
import subprocess
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.command_service import CommandService
from app.streaming.profile import (
    CameraTopology,
    CaptureFormat,
    StreamProfile,
    StreamState,
    series_input_format,
)
from app.streaming.pipeline import build_gst_argv, argv_to_str
from app.streaming.util import (
    ValidationError,
    previewable_formats,
    require_device,
    require_entity,
    require_int,
)
from app.streaming.configurators import get_configurator
from app.streaming.providers import get_provider
from app.streaming.transports import get_transport

logger = logging.getLogger(__name__)

# MJPEG frame chunk size for streaming reads.
_READ_CHUNK = 1 << 16
# Multipart delimiter written by ``multipartmux boundary=frame`` per JPEG frame.
# Counting these while bytes flow to the viewer gives a reliable measured FPS
# (browser <img> "load" events are not fired per frame in every engine).
_BOUNDARY_TOKEN = b"--frame\r\n"
# Max GX ROI / picture dimension (matches veye_viewer's 8192 sanity bound).
_MAX_DIM = 8192


@dataclass
class ActiveStream:
    """One running ``gst-launch-1.0`` capture pipeline plus its bookkeeping."""
    stream_id: str
    video_node: str
    profile: StreamProfile
    process: subprocess.Popen
    transport_name: str
    media_type: str
    started_at: float
    state: StreamState = StreamState.RUNNING
    stderr_tail: deque = field(default_factory=lambda: deque(maxlen=200))
    _stop_lock: threading.Lock = field(default_factory=threading.Lock)
    # Measured-FPS bookkeeping (guarded by its own lock, updated in the read loop).
    _frame_ts: deque = field(default_factory=deque)
    _frames_total: int = 0
    _fps_lock: threading.Lock = field(default_factory=threading.Lock)
    _carry: bytes = b""

    def note_bytes(self, data: bytes) -> None:
        """Count MJPEG frames delivered in ``data`` for real-time FPS metering.

        A single boundary token can straddle two reads, so a short tail is kept
        and re-examined; its length (token-1) guarantees no boundary is ever
        fully contained in the carried tail, so nothing is double counted.
        """
        now = time.monotonic()
        buf = self._carry + data
        n = buf.count(_BOUNDARY_TOKEN)
        self._carry = buf[-(len(_BOUNDARY_TOKEN) - 1):]
        if not n:
            return
        with self._fps_lock:
            self._frames_total += n
            for _ in range(n):
                self._frame_ts.append(now)
            cutoff = now - 3.0
            while self._frame_ts and self._frame_ts[0] < cutoff:
                self._frame_ts.popleft()

    def measured_fps(self) -> float:
        now = time.monotonic()
        window_start = now - 1.0
        with self._fps_lock:
            c = 0
            for ts in reversed(self._frame_ts):  # appended in ascending order
                if ts >= window_start:
                    c += 1
                else:
                    break
        return float(c)

    def info(self) -> Dict[str, Any]:
        alive = self.process.poll() is None
        return {
            "stream_id": self.stream_id,
            "video_node": self.video_node,
            "state": self.state.value if alive else StreamState.STOPPED.value,
            "alive": alive,
            "transport": self.transport_name,
            "media_type": self.media_type,
            "series": self.profile.series,
            "width": self.profile.width,
            "height": self.profile.height,
            "fps": self.profile.fps,
            "measured_fps": round(self.measured_fps(), 1) if alive else 0,
            "frames_total": self._frames_total,
            "uptime_s": round(time.time() - self.started_at, 1),
            "stderr_tail": list(self.stderr_tail)[-20:],
        }


class StreamService:
    """Coordinates configure / start / stop for GX live streams."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._streams: Dict[str, ActiveStream] = {}
        # device-node exclusivity: /dev/videoN -> stream_id currently capturing it
        self._owners: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    _SUPPORTED_SERIES = ("gx", "mv")

    @classmethod
    def _require_supported(cls, fmt: CaptureFormat) -> None:
        if (fmt.series or "gx").lower() not in cls._SUPPORTED_SERIES:
            raise ValidationError(
                "Live preview is only supported for the GX (UYVY) and MV/RAW "
                "(GREY) series."
            )

    @staticmethod
    def _validate_fmt(fmt: CaptureFormat) -> None:
        fmt.width = require_int(fmt.width, "width", 1, _MAX_DIM)
        fmt.height = require_int(fmt.height, "height", 1, _MAX_DIM)
        fmt.roi_x = require_int(fmt.roi_x, "roi_x", 0, _MAX_DIM)
        fmt.roi_y = require_int(fmt.roi_y, "roi_y", 0, _MAX_DIM)
        try:
            fps = float(fmt.fps)
        except (TypeError, ValueError):
            raise ValidationError(f"fps: not a number: {fmt.fps!r}")
        if not 0 < fps <= 240:
            raise ValidationError(f"fps: {fps} out of range (0, 240]")
        fmt.fps = fps

    @staticmethod
    def _validate_topology(topo: CameraTopology) -> None:
        require_device(topo.video_node, "video_node")
        if topo.media_node:
            require_device(topo.media_node, "media_node")
        if topo.video_subnode:
            require_device(topo.video_subnode, "video_subnode")
        if topo.media_entity_name:
            require_entity(topo.media_entity_name)

    # ------------------------------------------------------------------
    # GX capability resolution
    # ------------------------------------------------------------------
    def resolve_cap_mode(
        self, fmt: CaptureFormat, topo: CameraTopology, cmd: CommandService
    ) -> Optional[int]:
        """Return the GX VideoModeCap (1=ROI, 2=Preset), probing I2C if needed."""
        if fmt.cap_mode in (1, 2):
            return fmt.cap_mode
        cap = cmd.detect_video_mode_cap(topo.i2c_bus, topo.i2c_addr)
        fmt.cap_mode = cap
        return cap

    # ------------------------------------------------------------------
    # Configure (Stage 0 + I2C) - can run standalone or before start()
    # ------------------------------------------------------------------
    def configure(
        self,
        platform: str,
        topo: CameraTopology,
        fmt: CaptureFormat,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Prepare camera (sensor I2C + host pipeline) for GX capture.

        Returns a plan/summary dict; on failure ``ok`` is False with an ``error``.
        """
        self._require_supported(fmt)
        self._validate_fmt(fmt)
        self._validate_topology(topo)

        series = (fmt.series or "gx").lower()
        cmd = CommandService(camera_series=series)

        # ---- capability + I2C plan ---------------------------------------
        cap_mode: Optional[int] = None
        i2c_plan: List[Dict[str, Any]] = []
        if series == "mv":
            # MV/RAW: no VideoModeCap, always free ROI, I2C writes ``fps`` (x100).
            i2c_plan.append({"command_id": "fps", "params": [fmt.fps]})
        else:
            cap_mode = self.resolve_cap_mode(fmt, topo, cmd)
            if cap_mode is None:
                return {
                    "ok": False,
                    "error": "Could not determine GX VideoModeCap (ROI vs Preset). "
                             "Check I2C connectivity or specify the mode explicitly.",
                }
            fmt.cap_mode = cap_mode
            if cap_mode == 2:
                preset_mode = require_int(
                    fmt.preset_mode if fmt.preset_mode is not None else 0,
                    "preset_mode", 0, 7,
                )
                fmt.preset_mode = preset_mode
                i2c_plan.append({"command_id": "videomode", "params": [preset_mode]})
            i2c_plan.append({"command_id": "fps_write", "params": [fmt.fps]})

        mode = "roi" if (series == "mv" or cap_mode == 1) else "preset"

        # ---- host plan (Stage 0) -----------------------------------------
        configurator = get_configurator(platform)
        host_cmds = configurator.host_commands(topo, fmt)

        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "platform": platform,
                "series": series,
                "cap_mode": cap_mode,
                "mode": mode,
                "i2c": i2c_plan,
                "host": [argv_to_str(c) for c in host_cmds],
            }

        # ---- execute I2C --------------------------------------------------
        i2c_results: List[Dict[str, Any]] = []
        ok = True
        for step in i2c_plan:
            if not cmd.is_tools_available():
                return {
                    "ok": False,
                    "error": f"{series.upper()} I2C tools not found in tools/. "
                             "Cannot configure the sensor.",
                }
            r = cmd.execute_command(
                command_id=step["command_id"],
                i2c_bus=topo.i2c_bus,
                i2c_addr=topo.i2c_addr,
                params=step["params"],
                action="write",
            )
            step_ok = bool(r.get("success"))
            ok = ok and step_ok
            i2c_results.append({
                "command_id": step["command_id"],
                "params": step["params"],
                "ok": step_ok,
                "detail": r.get("stdout") or r.get("error") or r.get("stderr") or "",
            })

        # ---- execute host commands ---------------------------------------
        host_results: List[Dict[str, Any]] = []
        for argv in host_cmds:
            entry = self._run_host(argv)
            ok = ok and entry["ok"]
            host_results.append(entry)

        return {
            "ok": ok,
            "platform": platform,
            "series": series,
            "cap_mode": cap_mode,
            "mode": mode,
            "i2c": i2c_results,
            "host": host_results,
            "error": None if ok else "Configure reported failures (see i2c/host details).",
        }

    @staticmethod
    def _run_host(argv: List[str], timeout: int = 8) -> Dict[str, Any]:
        """Run a single host-side argv command (never through a shell)."""
        entry = {"cmd": argv_to_str(argv), "ok": False, "stderr": ""}
        if not argv or not shutil.which(argv[0]):
            entry["stderr"] = f"{argv[0] if argv else '?'} not found"
            return entry
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
            entry["ok"] = r.returncode == 0
            if not entry["ok"]:
                entry["stderr"] = (r.stderr or r.stdout or "").strip()[:400]
        except subprocess.TimeoutExpired:
            entry["stderr"] = f"timeout after {timeout}s"
        except Exception as e:  # noqa: BLE001 - surface any execution error to UI
            entry["stderr"] = str(e)
        return entry

    # ------------------------------------------------------------------
    # Start / stop
    # ------------------------------------------------------------------
    def start(
        self,
        platform: str,
        topo: CameraTopology,
        fmt: CaptureFormat,
        transport: str = "mjpeg",
        jpeg_quality: int = 85,
        skip_configure: bool = False,
    ) -> Dict[str, Any]:
        """Configure the camera and launch the capture pipeline.

        Returns {stream_id, playback_url, media_type, pipeline} on success or
        {ok: False, error} on failure.  The device node is held exclusively; a
        second start on the same node returns a 409-style busy error.
        """
        self._require_supported(fmt)
        self._validate_fmt(fmt)
        self._validate_topology(topo)
        require_device(topo.video_node, "video_node")
        video_node = topo.video_node

        if transport not in ("mjpeg",):
            return {"ok": False, "error": f"Unsupported transport for v1: {transport}"}

        with self._lock:
            owner = self._owners.get(video_node)
            if owner and owner in self._streams and self._streams[owner].process.poll() is None:
                return {
                    "ok": False,
                    "busy": True,
                    "error": f"{video_node} is already streaming (stream_id={owner}). "
                             "Stop it before starting a new preview.",
                }
            if owner and owner not in self._streams:
                self._owners.pop(video_node, None)

        # ---- configure ----------------------------------------------------
        configure_result: Optional[Dict[str, Any]] = None
        if not skip_configure:
            configure_result = self.configure(platform, topo, fmt)
            if not configure_result.get("ok"):
                return {
                    "ok": False,
                    "error": configure_result.get("error") or "configure failed",
                    "configure": configure_result,
                }

        # ---- build profile + pipeline -------------------------------------
        series = (fmt.series or "gx").lower()
        cap_mode = fmt.cap_mode
        provider = get_provider(platform)
        trans = get_transport(transport)
        jpeg_quality = max(1, min(100, int(jpeg_quality)))

        profile = StreamProfile(
            stream_id="",
            platform=platform,
            series=series,
            video_node=video_node,
            width=int(fmt.width),
            height=int(fmt.height),
            fps=int(round(fmt.fps)),
            transport=transport,
            encoder="jpeg",
            jpeg_quality=jpeg_quality,
            topology=topo,
            fmt=fmt,
            input_format=series_input_format(series),
        )
        try:
            argv = build_gst_argv(profile, provider, trans)
        except Exception as e:  # noqa: BLE001
            logger.exception("Failed to build pipeline")
            return {"ok": False, "error": f"pipeline build failed: {e}"}

        if shutil.which("gst-launch-1.0") is None:
            return {
                "ok": False,
                "error": "gst-launch-1.0 not found. Install GStreamer "
                         "(good + jpeg plugins) on the board.",
                "pipeline": argv_to_str(argv),
            }

        stream_id = uuid.uuid4().hex[:12]
        profile.stream_id = stream_id

        try:
            proc = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("Failed to launch gst-launch")
            return {"ok": False, "error": f"launch failed: {e}", "pipeline": argv_to_str(argv)}

        active = ActiveStream(
            stream_id=stream_id,
            video_node=video_node,
            profile=profile,
            process=proc,
            transport_name=trans.name,
            media_type=trans.media_type,
            started_at=time.time(),
        )
        # Drain stderr in the background so a full pipe never blocks gst-launch.
        threading.Thread(
            target=self._drain_stderr, args=(active,), daemon=True, name=f"gsterr-{stream_id}"
        ).start()

        with self._lock:
            self._streams[stream_id] = active
            self._owners[video_node] = stream_id

        logger.info("Started stream %s on %s: %s", stream_id, video_node, argv_to_str(argv))
        return {
            "ok": True,
            "stream_id": stream_id,
            "playback_url": trans.playback_url(stream_id),
            "media_type": trans.media_type,
            "pipeline": argv_to_str(argv),
            "series": series,
            "cap_mode": cap_mode,
            "configure": configure_result,
        }

    @staticmethod
    def _drain_stderr(active: ActiveStream) -> None:
        stream = active.process.stderr
        if stream is None:
            return
        try:
            for raw in iter(stream.readline, b""):
                if not raw:
                    break
                active.stderr_tail.append(raw.decode("utf-8", "replace").rstrip("\n"))
        except Exception:  # noqa: BLE001 - process closed
            pass
        finally:
            try:
                stream.close()
            except Exception:  # noqa: BLE001
                pass

    def stop(self, stream_id: str) -> Dict[str, Any]:
        """Terminate a single stream and release its device node."""
        with self._lock:
            active = self._streams.pop(stream_id, None)
        if active is None:
            return {"ok": True, "stopped": False, "error": None, "stream_id": stream_id}

        with active._stop_lock:
            proc = active.process
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
            for pipe in (proc.stdout,):
                if pipe:
                    try:
                        pipe.close()
                    except Exception:  # noqa: BLE001
                        pass
            active.state = StreamState.STOPPED

        with self._lock:
            if self._owners.get(active.video_node) == stream_id:
                self._owners.pop(active.video_node, None)

        logger.info("Stopped stream %s (%s)", stream_id, active.video_node)
        return {"ok": True, "stopped": True, "stream_id": stream_id}

    def shutdown(self) -> None:
        """Stop every active stream (called on app shutdown)."""
        with self._lock:
            ids = list(self._streams.keys())
        for sid in ids:
            self.stop(sid)

    # ------------------------------------------------------------------
    # Streaming reader
    # ------------------------------------------------------------------
    async def stream_chunks(self, stream_id: str):
        """Async generator yielding raw MJPEG bytes from the pipeline stdout.

        The pipeline is torn down when the consumer disconnects (browser closes
        the <img>) or the process exits, so a preview never outlives its viewer.
        """
        with self._lock:
            active = self._streams.get(stream_id)
        if active is None or active.process.stdout is None:
            raise KeyError(stream_id)

        fd = active.process.stdout.fileno()
        loop = asyncio.get_event_loop()
        try:
            while True:
                try:
                    chunk = await loop.run_in_executor(None, os.read, fd, _READ_CHUNK)
                except OSError:
                    break
                if not chunk:
                    break
                active.note_bytes(chunk)
                yield chunk
        finally:
            self.stop(stream_id)

    # ------------------------------------------------------------------
    # Status / capabilities
    # ------------------------------------------------------------------
    def status(self, stream_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            if stream_id:
                active = self._streams.get(stream_id)
                return {"streams": [active.info()] if active else [], "count": 1 if active else 0}
            streams = [s.info() for s in self._streams.values()]
            return {"streams": streams, "count": len(streams), "owners": dict(self._owners)}

    def get(self, stream_id: str) -> Optional[ActiveStream]:
        with self._lock:
            return self._streams.get(stream_id)

    def media_type(self, stream_id: str) -> Optional[str]:
        active = self.get(stream_id)
        return active.media_type if active else None

    def read_current_picture(
        self, series: str, i2c_bus: int, i2c_addr: str
    ) -> Dict[str, Any]:
        """Read the camera's current ROI + framerate so the panel can prefill.

        Reuses the existing ``roi`` / ``fps`` read commands via CommandService.
        ``roi`` reads [offset_x, offset_y, width, height] (raw); ``fps`` is raw
        register value (MV x100, GX x10000).  Best-effort: returns {} (or a
        partial dict) if a read fails, so the panel falls back to defaults.
        """
        cur: Dict[str, Any] = {}
        if i2c_bus is None:
            return cur
        try:
            svc = CommandService(camera_series=series)
            roi = svc.execute_command(
                command_id="roi", i2c_bus=i2c_bus, i2c_addr=i2c_addr,
                params=[], action="read",
            )
            rv = roi.get("read_values") or []
            if len(rv) >= 4:
                cur["roi_x"] = int(rv[0])
                cur["roi_y"] = int(rv[1])
                cur["width"] = int(rv[2])
                cur["height"] = int(rv[3])
            fps_div = 100 if series == "mv" else 10000
            fr = svc.execute_command(
                command_id="fps", i2c_bus=i2c_bus, i2c_addr=i2c_addr,
                params=[], action="read",
            )
            fv = fr.get("read_values") or []
            if fv:
                cur["fps"] = round(int(fv[0]) / fps_div, 2)
        except Exception:  # noqa: BLE001 - prefill is best-effort only
            return cur
        return cur

    def get_capabilities(
        self,
        platform: str,
        video_node: str,
        i2c_bus: Optional[int] = None,
        i2c_addr: str = "0x3b",
        series: str = "gx",
    ) -> Dict[str, Any]:
        """Report previewable formats + platform encode/transport support."""
        provider = get_provider(platform)
        series = (series or "gx").lower()
        result: Dict[str, Any] = {
            "platform": platform,
            "series": series,
            "series_supported": ["gx", "mv"],
            "provider": provider.capabilities(),
            "formats": [],
        }
        if video_node:
            try:
                require_device(video_node, "video_node")
            except ValidationError as e:
                result["error"] = str(e)
                return result
            if shutil.which("v4l2-ctl"):
                try:
                    r = subprocess.run(
                        ["v4l2-ctl", "-d", video_node, "--list-formats-ext"],
                        capture_output=True, text=True, timeout=6,
                    )
                    result["formats"] = previewable_formats(r.stdout)
                except Exception as e:  # noqa: BLE001
                    result["formats_error"] = str(e)
            else:
                result["formats_error"] = "v4l2-ctl not found"
        # Optional GX capability hint (ROI vs Preset) for the UI.  Mirrors the
        # resolution/framerate page: read VideoModeCap (0x005C) and, for Preset
        # cameras, enumerate the actual preset modes (resolution + framerate)
        # so the Live Preview panel can drive its UI from the camera capability
        # instead of asking the user to pick the mode manually.
        # MV/RAW has no VideoModeCap register, so this is GX-only.
        if series == "gx" and i2c_bus is not None:
            try:
                svc = CommandService(camera_series="gx")
                cap = svc.detect_video_mode_cap(i2c_bus, i2c_addr)
                result["video_mode_cap"] = cap
                if cap == 2:
                    preset_count = max(svc.get_preset_mode_count(i2c_bus, i2c_addr), 1)
                    result["preset_count"] = preset_count
                    result["preset_modes"] = svc.read_preset_mode_data(
                        i2c_bus, i2c_addr, preset_count
                    )
            except Exception:  # noqa: BLE001
                result["video_mode_cap"] = None
        # Prefill for ROI-mode cameras.  MV/RAW is always ROI; GX uses ROI only
        # when VideoModeCap==1 (or detection failed and the UI fell back to
        # editable W/H/FPS).  GX preset cameras (cap==2) drive the panel through
        # the preset selector instead, so we skip the extra I2C reads there.
        if i2c_bus is not None and result.get("video_mode_cap") != 2:
            result["current"] = self.read_current_picture(series, i2c_bus, i2c_addr)
        return result


# Module-level singleton used by the API router and app lifespan.
stream_service = StreamService()
