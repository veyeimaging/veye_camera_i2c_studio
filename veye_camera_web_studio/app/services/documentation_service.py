"""Documentation service - provides register map and wiki-style documentation."""
import json
import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
REFERENCE_DIR = os.path.join(BASE_DIR, "config")  # gx_register.json is also copied here if needed


class DocumentationService:
    """Provides register documentation from gx_register.json and commands metadata."""

    def __init__(self):
        self._register_map = None
        self._commands = None

    def load_register_map(self) -> List[Dict[str, Any]]:
        """Load the GX register map from JSON."""
        if self._register_map is None:
            path = os.path.join(REFERENCE_DIR, "gx_register.json")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._register_map = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load register map: {e}")
                self._register_map = []
        return self._register_map

    def load_commands(self) -> List[Dict[str, Any]]:
        """Load commands metadata."""
        if self._commands is None:
            path = os.path.join(CONFIG_DIR, "commands.json")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._commands = data.get("commands", [])
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load commands: {e}")
                self._commands = []
        return self._commands

    def get_register_by_address(self, address: str) -> Optional[Dict[str, Any]]:
        """Look up a register definition by hex address."""
        addr_upper = address.upper()
        for reg in self.load_register_map():
            if reg.get("address", "").upper() == addr_upper:
                return reg
        return None

    def get_full_documentation(self, command_id: str) -> Dict[str, Any]:
        """Build complete documentation for a command, merging register map + command metadata."""
        commands = self.load_commands()
        cmd = None
        for c in commands:
            if c["id"] == command_id:
                cmd = c
                break
        if not cmd:
            return {"error": f"Command not found: {command_id}"}

        doc = dict(cmd)

        # Enrich with register map data
        reg_addr = cmd.get("register", {}).get("address")
        if reg_addr:
            reg_info = self.get_register_by_address(reg_addr)
            if reg_info:
                doc["register_info"] = reg_info

        return doc

    def get_all_registers(self) -> List[Dict[str, Any]]:
        """Return the complete register map."""
        return self.load_register_map()

    def get_registers_by_group(self, group_id: str) -> List[Dict[str, Any]]:
        """Return register definitions for commands in a specific group."""
        commands = self.load_commands()
        group_cmds = [c for c in commands if c.get("group") == group_id]
        registers = []
        for cmd in group_cmds:
            reg_addr = cmd.get("register", {}).get("address")
            if reg_addr:
                reg_info = self.get_register_by_address(reg_addr)
                if reg_info:
                    entry = dict(reg_info)
                    entry["command_id"] = cmd["id"]
                    entry["command_name"] = cmd["name"]
                    registers.append(entry)
        return registers
