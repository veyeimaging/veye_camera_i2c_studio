"""Command API routes - command catalog, execution, and documentation."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, validator
from typing import Dict, Any, List, Optional
import logging

from app.services.command_service import CommandService
from app.services.documentation_service import DocumentationService
from app.services.log_service import LogService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["commands"])

# Singleton services
_command_service = CommandService()
_doc_service = DocumentationService()
_log_service = LogService()


class ExecuteRequest(BaseModel):
    command_id: str
    i2c_bus: int = 10
    i2c_addr: str = "0x3b"
    params: List[Any] = []
    timeout: int = 5
    action: Optional[str] = None  # "read" or "write"; for rw commands

    @validator('i2c_bus')
    def validate_i2c_bus(cls, v):
        """Validate I2C bus number (typically 0-20)."""
        if not 0 <= v <= 20:
            raise ValueError('I2C bus must be between 0 and 20')
        return v

    @validator('i2c_addr')
    def validate_i2c_addr(cls, v):
        """Validate I2C address (0x00-0x7F for 7-bit addressing)."""
        try:
            addr = int(v, 16) if v.startswith('0x') or v.startswith('0X') else int(v)
            if not 0 <= addr <= 0x7F:
                raise ValueError('I2C address must be between 0x00 and 0x7F')
        except ValueError as e:
            if 'I2C address' in str(e):
                raise
            raise ValueError('Invalid I2C address format')
        return v

    @validator('timeout')
    def validate_timeout(cls, v):
        """Validate timeout (1-30 seconds)."""
        if not 1 <= v <= 30:
            raise ValueError('Timeout must be between 1 and 30 seconds')
        return v


@router.get("/commands/groups")
def get_command_groups() -> Dict[str, Any]:
    """Get all command groups."""
    return _command_service.load_groups()


@router.get("/commands")
def get_commands(
    group: Optional[str] = None,
    search: Optional[str] = None,
    lang: str = Query("en", regex="^(en|zh)$"),
    i2c_bus: Optional[int] = None,
    i2c_addr: Optional[str] = None,
) -> Dict[str, Any]:
    """Get commands, optionally filtered by group or search query.
    For video_modes group: pass i2c_bus and i2c_addr to enable capability-based filtering."""
    if search:
        results = _command_service.search_commands(search, lang)
        return {"commands": results, "count": len(results)}
    if group:
        # Special handling for video_modes group: detect capability and filter
        if group == "video_modes" and i2c_bus is not None and i2c_addr is not None:
            cap_mode = _command_service.detect_video_mode_cap(i2c_bus, i2c_addr)
            if cap_mode is not None:
                preset_count = 0
                preset_modes = []
                if cap_mode == 2:
                    preset_count = _command_service.get_preset_mode_count(i2c_bus, i2c_addr)
                    preset_count = max(preset_count, 1)  # at least 1
                    preset_modes = _command_service.read_preset_mode_data(
                        i2c_bus, i2c_addr, preset_count
                    )
                results = _command_service.get_commands_for_video_mode(cap_mode, preset_count)
                resp: Dict[str, Any] = {
                    "commands": results,
                    "count": len(results),
                    "video_mode_info": {
                        "cap_mode": cap_mode,
                        "cap_label": {"en": "ROI Mode" if cap_mode == 1 else "Preset Mode",
                                      "zh": "ROI 模式" if cap_mode == 1 else "预设模式"},
                        "preset_count": preset_count if cap_mode == 2 else 0,
                        "preset_modes": preset_modes,
                    },
                }
                return resp
            else:
                # Capability detection failed, return all video_modes commands
                logger.warning("Failed to detect VideoModeCap, returning all video_modes commands")
        results = _command_service.get_commands_by_group(group)
        return {"commands": results, "count": len(results)}
    data = _command_service.load_commands()
    return {"commands": data.get("commands", []), "count": len(data.get("commands", []))}


@router.get("/commands/{command_id}")
def get_command(command_id: str) -> Dict[str, Any]:
    """Get a single command definition."""
    cmd = _command_service.get_command(command_id)
    if not cmd:
        raise HTTPException(status_code=404, detail=f"Command not found: {command_id}")
    return cmd


@router.post("/commands/{command_id}/execute")
def execute_command(command_id: str, request: ExecuteRequest) -> Dict[str, Any]:
    """Execute a camera command."""
    command = _command_service.get_command(command_id)
    if not command:
        raise HTTPException(status_code=404, detail=f"Command not found: {command_id}")

    # Check if I2C tools are available
    if not _command_service.is_tools_available():
        # Return simulated response for demo mode
        result = {
            "success": False,
            "stdout": "",
            "stderr": "i2c_vread/i2c_vwrite not found in tools/. Running in demo mode.",
            "returncode": -1,
            "duration_ms": 0,
            "demo_mode": True,
            "command": f"(simulated) i2c_v{'read' if command['mode'] in ('read','rw') else 'write'} {command_id}",
        }
    else:
        result = _command_service.execute_command(
            command_id=command_id,
            i2c_bus=request.i2c_bus,
            i2c_addr=request.i2c_addr,
            params=request.params,
            timeout=request.timeout,
            action=request.action,
        )

    # Log the operation
    _log_service.record(
        command_id=command_id,
        mode=command["mode"],
        i2c_bus=request.i2c_bus,
        i2c_addr=request.i2c_addr,
        params=request.params,
        result=result,
    )

    return result


@router.get("/docs/{command_id}")
def get_command_docs(command_id: str) -> Dict[str, Any]:
    """Get full documentation for a command (merged with register map)."""
    doc = _doc_service.get_full_documentation(command_id)
    if "error" in doc:
        raise HTTPException(status_code=404, detail=doc["error"])
    return doc


@router.get("/docs")
def get_all_registers() -> Dict[str, Any]:
    """Get the complete register map."""
    registers = _doc_service.get_all_registers()
    return {"registers": registers, "count": len(registers)}


@router.get("/logs")
def get_logs(limit: int = Query(100, ge=1, le=10000), offset: int = Query(0, ge=0)) -> Dict[str, Any]:
    """Get operation logs."""
    logs = _log_service.get_logs(limit=limit, offset=offset)
    total = _log_service.get_log_count()
    return {"logs": logs, "total": total, "limit": limit, "offset": offset}


@router.delete("/logs")
def clear_logs() -> Dict[str, str]:
    """Clear all operation logs."""
    _log_service.clear_logs()
    return {"status": "cleared"}


@router.get("/logs/export")
def export_logs() -> Dict[str, str]:
    """Export all logs as JSON."""
    return {"data": _log_service.export_logs()}
