"""Command execution service - directly calls i2c_vread / i2c_vwrite."""
import subprocess
import os
import json
import logging
import threading
import ast
import operator
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Paths (all tools live inside the project's own tools/ directory)
_BASE = os.path.join(os.path.dirname(__file__), "..", "..")
_CONFIG_DIR = os.path.join(_BASE, "config")
_TOOLS_DIR = os.path.join(_BASE, "tools")
_I2C_VREAD = os.path.join(_TOOLS_DIR, "i2c_vread")
_I2C_VWRITE = os.path.join(_TOOLS_DIR, "i2c_vwrite")

# Mutex – only one I2C transaction at a time
_i2c_lock = threading.Lock()


class CommandService:
    """Executes VEYE camera I2C commands by calling i2c_vread / i2c_vwrite
    directly (no shell wrapper needed)."""

    def __init__(self):
        self._commands_cache: Optional[Dict] = None
        self._groups_cache: Optional[Dict] = None

    # ------------------------------------------------------------------
    # Configuration loaders
    # ------------------------------------------------------------------
    def load_commands(self) -> Dict[str, Any]:
        if self._commands_cache is None:
            with open(os.path.join(_CONFIG_DIR, "commands.json"), "r", encoding="utf-8") as f:
                self._commands_cache = json.load(f)
        return self._commands_cache

    def load_groups(self) -> Dict[str, Any]:
        if self._groups_cache is None:
            with open(os.path.join(_CONFIG_DIR, "command_groups.json"), "r", encoding="utf-8") as f:
                self._groups_cache = json.load(f)
        return self._groups_cache

    def get_command(self, command_id: str) -> Optional[Dict[str, Any]]:
        for cmd in self.load_commands().get("commands", []):
            if cmd["id"] == command_id:
                return cmd
        return None

    def get_commands_by_group(self, group_id: str) -> List[Dict[str, Any]]:
        return [c for c in self.load_commands().get("commands", []) if c.get("group") == group_id]

    # ------------------------------------------------------------------
    # Video mode capability detection & filtering
    # ------------------------------------------------------------------
    def detect_video_mode_cap(self, i2c_bus: int, i2c_addr: str) -> Optional[int]:
        """Read register 0x005C (VideoModeCap).
        Returns 1=ROI mode, 2=Preset mode, or None on failure."""
        r = self._run_i2c_vread(i2c_bus, i2c_addr, "0x005C", 0, 3)
        if r["ok"]:
            try:
                val = int(r["raw"])
                if val & 0x1:
                    return 1  # ROI mode
                if val & 0x2:
                    return 2  # Preset mode
                return val if val > 0 else None
            except (ValueError, TypeError):
                pass
        return None

    def get_preset_mode_count(self, i2c_bus: int, i2c_addr: str) -> int:
        """Read register 0x0060 (VideoModeNum). Returns number of supported preset modes (0-8)."""
        r = self._run_i2c_vread(i2c_bus, i2c_addr, "0x0060", 0, 3)
        if r["ok"]:
            try:
                val = int(r["raw"])
                return min(val, 8)
            except (ValueError, TypeError):
                pass
        return 0

    def get_commands_for_video_mode(
        self, cap_mode: int, preset_count: int = 8
    ) -> List[Dict[str, Any]]:
        """Return commands in the video_modes group filtered by capability mode.

        cap_mode: 1=ROI, 2=Preset
        preset_count: number of preset modes to include (1-8, only for cap_mode=2)
        """
        all_cmds = self.load_commands().get("commands", [])
        result = []
        for c in all_cmds:
            if c.get("group") != "video_modes":
                continue
            cmd_cap_modes = c.get("cap_modes")
            if cmd_cap_modes is None:
                # Always shown in video_modes
                result.append(c)
                continue
            if cap_mode in cmd_cap_modes:
                # For preset mode, filter by preset_count
                if cap_mode == 2:
                    cid = c["id"]
                    skip = False
                    for prefix in ("videomodewh", "videomodeparam"):
                        if cid.startswith(prefix):
                            try:
                                mode_num = int(cid[len(prefix):])
                                if mode_num > preset_count:
                                    skip = True
                            except ValueError:
                                pass
                            break
                    if skip:
                        continue
                result.append(c)
        return result

    def read_preset_mode_data(
        self, i2c_bus: int, i2c_addr: str, preset_count: int
    ) -> List[Dict[str, Any]]:
        """Read resolution and framerate for each supported preset mode.

        Returns list of dicts: [{mode, width, height, fps, read_mode}, ...]
        """
        modes = []
        for i in range(1, preset_count + 1):
            wh_reg = 0x0064 + (i - 1) * 8
            param_reg = 0x0068 + (i - 1) * 8

            wh_r = self._run_i2c_vread(i2c_bus, i2c_addr, f"0x{wh_reg:04X}", 0, 3)
            param_r = self._run_i2c_vread(i2c_bus, i2c_addr, f"0x{param_reg:04X}", 0, 3)

            width = height = fps = read_mode_val = 0
            if wh_r["ok"]:
                try:
                    wh_val = int(wh_r["raw"])
                    width = (wh_val >> 16) & 0xFFFF
                    height = wh_val & 0xFFFF
                except (ValueError, TypeError):
                    pass
            if param_r["ok"]:
                try:
                    param_val = int(param_r["raw"])
                    read_mode_val = (param_val >> 16) & 0xFF
                    fps = param_val & 0xFFFF
                except (ValueError, TypeError):
                    pass

            read_mode_names = {0: "Normal", 1: "Binning", 2: "Subsampling"}
            modes.append({
                "mode": i - 1,
                "width": width,
                "height": height,
                "fps_raw": fps,
                "fps": round(fps / 100, 2) if fps > 100 else fps,
                "read_mode": read_mode_val,
                "read_mode_name": read_mode_names.get(read_mode_val, str(read_mode_val)),
            })
        return modes

    def search_commands(self, query: str, lang: str = "en") -> List[Dict[str, Any]]:
        q = query.lower()
        results = []
        for cmd in self.load_commands().get("commands", []):
            if (q in cmd.get("name", {}).get(lang, "").lower()
                    or q in cmd.get("description", {}).get(lang, "").lower()
                    or q in cmd.get("id", "").lower()):
                results.append(cmd)
        return results

    # ------------------------------------------------------------------
    # Parameter validation
    # ------------------------------------------------------------------
    @staticmethod
    def validate_params(command: Dict[str, Any], params: List[Any]) -> Optional[str]:
        cmd_params = command.get("parameters", [])
        required_count = sum(1 for p in cmd_params if p.get("required", True))
        if len(params) < required_count:
            return f"Missing required parameters (expected {required_count}, got {len(params)})"

        for i, (pdef, val) in enumerate(zip(cmd_params, params)):
            ptype = pdef.get("type", "integer")
            lo, hi = pdef.get("min"), pdef.get("max")
            if ptype in ("integer", "float"):
                try:
                    num = float(val) if ptype == "float" else int(float(val))
                except (ValueError, TypeError):
                    return f"Parameter {i+1}: invalid numeric value '{val}'"
                if lo is not None and num < lo:
                    return f"Parameter {i+1}: {num} below minimum {lo}"
                if hi is not None and num > hi:
                    return f"Parameter {i+1}: {num} above maximum {hi}"
            elif ptype == "enum":
                valid = [o["value"] for o in pdef.get("options", [])]
                try:
                    if int(float(val)) not in valid:
                        return f"Parameter {i+1}: invalid enum value {val}"
                except (ValueError, TypeError):
                    return f"Parameter {i+1}: invalid enum value '{val}'"
        return None

    # ------------------------------------------------------------------
    # Low-level I2C helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _run_i2c_vread(bus: int, addr: str, reg: str, reg_type: int, timeout: int) -> Dict:
        """Call i2c_vread <bus> <addr> <reg> <reg_type> and return parsed result."""
        import time
        # Small delay to ensure I2C bus is ready (especially after switching registers)
        time.sleep(0.05)  # 50ms
        
        cmd = [_I2C_VREAD, str(bus), addr, str(reg), str(reg_type)]
        logger.debug("i2c_vread: %s", " ".join(cmd))
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=_TOOLS_DIR)
            raw = r.stdout.strip().split("\n")[-1] if r.stdout.strip() else ""
            logger.info(f"i2c_vread reg={reg} raw={raw} stderr={r.stderr.strip()}")
            return {"ok": r.returncode == 0, "raw": raw, "stderr": r.stderr.strip()}
        except subprocess.TimeoutExpired:
            return {"ok": False, "raw": "", "stderr": f"i2c_vread timed out ({timeout}s)"}
        except Exception as e:
            return {"ok": False, "raw": "", "stderr": str(e)}

    @staticmethod
    def _run_i2c_vwrite(bus: int, addr: str, reg: str, value: int, timeout: int) -> Dict:
        """Call i2c_vwrite <bus> <addr> <reg> <value> and return result."""
        cmd = [_I2C_VWRITE, str(bus), addr, str(reg), str(value)]
        logger.debug("i2c_vwrite: %s", " ".join(cmd))
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=_TOOLS_DIR)
            raw = r.stdout.strip()
            return {"ok": r.returncode == 0, "raw": raw, "stderr": r.stderr.strip()}
        except subprocess.TimeoutExpired:
            return {"ok": False, "raw": "", "stderr": f"i2c_vwrite timed out ({timeout}s)"}
        except Exception as e:
            return {"ok": False, "raw": "", "stderr": str(e)}

    # ------------------------------------------------------------------
    # Expression evaluator for value_expr / dynamic register addresses
    # ------------------------------------------------------------------
    # Safe operators for AST-based expression evaluation
    _SAFE_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    @classmethod
    def _safe_eval_node(cls, node: ast.AST) -> Any:
        """Recursively evaluate AST nodes safely."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = cls._safe_eval_node(node.left)
            right = cls._safe_eval_node(node.right)
            op_type = type(node.op)
            if op_type in cls._SAFE_OPERATORS:
                return cls._SAFE_OPERATORS[op_type](left, right)
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        elif isinstance(node, ast.UnaryOp):
            operand = cls._safe_eval_node(node.operand)
            op_type = type(node.op)
            if op_type in cls._SAFE_OPERATORS:
                return cls._SAFE_OPERATORS[op_type](operand)
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in ('int', 'float', 'round', 'abs'):
                    args = [cls._safe_eval_node(arg) for arg in node.args]
                    return {'int': int, 'float': float, 'round': round, 'abs': abs}[func_name](*args)
            raise ValueError("Unsupported function call")
        else:
            raise ValueError(f"Unsupported expression type: {type(node).__name__}")

    @staticmethod
    def _eval_expr(expr: str, params: List[Any], read_values: List[int]) -> Any:
        """Safely evaluate a value_expr like '{param0}' or 'int(round({param0} * 10))'.
        
        Uses AST parsing instead of eval() for security.
        """
        s = str(expr)
        # Substitute {paramN}
        for i, v in enumerate(params):
            s = s.replace(f"{{param{i}}}", str(v))
        # Substitute {readN}
        for i, v in enumerate(read_values):
            s = s.replace(f"{{read{i}}}", str(v))
        
        # Try to parse as a simple number first
        try:
            return int(s) if '.' not in s else float(s)
        except (ValueError, TypeError):
            pass
        
        # Parse and evaluate safely using AST
        try:
            tree = ast.parse(s, mode='eval')
            return CommandService._safe_eval_node(tree.body)
        except Exception:
            # If parsing fails, return the substituted string
            return s

    # ------------------------------------------------------------------
    # Main execution entry point
    # ------------------------------------------------------------------
    def execute_command(
        self,
        command_id: str,
        i2c_bus: int = 10,
        i2c_addr: str = "0x3b",
        params: Optional[List[Any]] = None,
        timeout: int = 5,
    ) -> Dict[str, Any]:
        """Execute a command by running its execution_steps against i2c_vread/vwrite."""
        logger.info(f"execute_command: command_id={command_id} i2c_bus={i2c_bus} i2c_addr={i2c_addr} params={params}")
        command = self.get_command(command_id)
        if not command:
            return self._err(f"Unknown command: {command_id}")

        params = params or []
        steps = command.get("execution_steps", [])
        if not steps:
            return self._err(f"Command '{command_id}' has no execution_steps")

        # For RW commands: decide read vs write based on params presence.
        # For read-only commands: only run read steps.
        # For write-only commands: only run write steps.
        mode = command["mode"]
        if mode == "read":
            steps = [s for s in steps if s["op"] == "read"]
        elif mode == "write":
            steps = [s for s in steps if s["op"] == "write"]
        elif mode == "rw":
            if params:
                # Write mode: only execute write steps
                steps = [s for s in steps if s["op"] == "write"]
            else:
                # Read mode: only execute read steps
                steps = [s for s in steps if s["op"] == "read"]

        if not steps:
            return self._err(f"No executable steps for mode='{mode}' with params={params}")

        # Validate params for write steps
        if command["mode"] in ("write", "rw") and params:
            err = self.validate_params(command, params)
            if err:
                return self._err(err)

        start = datetime.now()
        read_values: List[int] = []
        output_lines: List[str] = []
        all_ok = True

        # Acquire I2C lock
        acquired = _i2c_lock.acquire(timeout=timeout)
        if not acquired:
            return self._err("I2C bus busy (lock timeout)")

        try:
            for idx, step in enumerate(steps):
                op = step["op"]
                reg = step["reg"]
                reg_type = step.get("reg_type", 0)

                # Resolve dynamic register address (e.g. snsreg: "{param0}")
                if "{" in str(reg):
                    reg = str(self._eval_expr(reg, params, read_values))

                if op == "read":
                    r = self._run_i2c_vread(i2c_bus, i2c_addr, reg, reg_type, timeout)
                    if r["ok"]:
                        try:
                            val = int(r["raw"])
                        except ValueError:
                            val = r["raw"]
                        read_values.append(val if isinstance(val, int) else 0)
                        output_lines.append(f"Read [{reg}] = {r['raw']}")
                    else:
                        all_ok = False
                        output_lines.append(f"Read [{reg}] FAILED: {r['stderr']}")

                elif op == "write":
                    val_expr = step.get("value_expr", "0")
                    value = self._eval_expr(val_expr, params, read_values)
                    value = int(value) if not isinstance(value, int) else value
                    r = self._run_i2c_vwrite(i2c_bus, i2c_addr, reg, value, timeout)
                    if r["ok"]:
                        output_lines.append(f"Write [{reg}] = {value}  OK")
                    else:
                        all_ok = False
                        output_lines.append(f"Write [{reg}] = {value}  FAILED: {r['stderr']}")

            duration = (datetime.now() - start).total_seconds() * 1000
            return {
                "success": all_ok,
                "stdout": "\n".join(output_lines),
                "stderr": "",
                "returncode": 0 if all_ok else 1,
                "duration_ms": round(duration, 1),
                "read_values": read_values,
                "command": f"i2c_v{'read' if steps[0]['op']=='read' else 'write'} (direct)",
            }

        except Exception as e:
            logger.exception("Execution error for %s", command_id)
            duration = (datetime.now() - start).total_seconds() * 1000
            return self._err(str(e), duration_ms=round(duration, 1))
        finally:
            if _i2c_lock.locked():
                _i2c_lock.release()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _err(msg: str, duration_ms: float = 0) -> Dict[str, Any]:
        return {"success": False, "error": msg, "stdout": "", "stderr": msg,
                "returncode": -1, "duration_ms": duration_ms}

    def is_tools_available(self) -> bool:
        """Check if i2c_vread and i2c_vwrite binaries exist."""
        return os.path.isfile(_I2C_VREAD) and os.path.isfile(_I2C_VWRITE)
