"""Operation log service - records and manages command execution logs."""
import json
import os
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "operations.jsonl")


class LogService:
    """Records command execution operations to a JSONL log file."""

    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)

    def record(
        self,
        command_id: str,
        mode: str,
        i2c_bus: int,
        i2c_addr: str,
        params: List[Any],
        result: Dict[str, Any],
    ):
        """Record a command execution to the log."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "command_id": command_id,
            "mode": mode,
            "i2c_bus": i2c_bus,
            "i2c_addr": i2c_addr,
            "params": params,
            "success": result.get("success", False),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "returncode": result.get("returncode", -1),
            "duration_ms": result.get("duration_ms", 0),
        }
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write log: {e}")

    def get_logs(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Read recent log entries (newest first)."""
        if not os.path.isfile(LOG_FILE):
            return []
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            entries = []
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            # Return newest first, with pagination
            entries.reverse()
            return entries[offset:offset + limit]
        except Exception as e:
            logger.error(f"Failed to read logs: {e}")
            return []

    def get_log_count(self) -> int:
        """Return total number of log entries."""
        if not os.path.isfile(LOG_FILE):
            return 0
        try:
            with open(LOG_FILE, "r") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0

    def clear_logs(self):
        """Clear all log entries."""
        try:
            if os.path.isfile(LOG_FILE):
                os.remove(LOG_FILE)
                logger.info("Operation logs cleared")
        except Exception as e:
            logger.error(f"Failed to clear logs: {e}")

    def export_logs(self) -> str:
        """Export all logs as a JSON string."""
        entries = self.get_logs(limit=10000)
        return json.dumps(entries, indent=2, ensure_ascii=False)
