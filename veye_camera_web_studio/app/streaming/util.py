"""Validation + small helpers for the streaming subsystem.

Commands are always executed as argv lists (``shell=False``), which already
avoids shell metacharacter injection.  On top of that we whitelist every value
that originates from the browser / kernel topology before it is placed into an
argv element, mirroring the ``reInt`` / ``isSafeCmdToken`` checks in veye_viewer.
"""
from __future__ import annotations

import re
from typing import List

# /dev/videoN, /dev/mediaN, /dev/v4l-subdevN
_DEV_RE = re.compile(r"^/dev/[A-Za-z0-9_.-]{1,32}$")
_INT_RE = re.compile(r"^[0-9]{1,6}$")
# media-ctl entity names look like: gxcam 10-003b  (letters/digits/space/-/_)
_ENTITY_RE = re.compile(r"^[A-Za-z0-9 .:_/@-]{1,64}$")
# fourcc / media code: UYVY, GREY, UYVY8_2X8, Y8_1X8 ...
_FMT_RE = re.compile(r"^[A-Za-z0-9_]{1,16}$")


class ValidationError(ValueError):
    """Raised when a browser-supplied value fails whitelist validation."""


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValidationError(msg)


def is_safe_device(path: str) -> bool:
    return bool(_DEV_RE.match(path or ""))


def require_device(path: str, label: str) -> str:
    _require(is_safe_device(path), f"{label}: invalid device node {path!r}")
    return path


def require_entity(name: str) -> str:
    # Reject quotes / backticks / newlines outright, then whitelist the rest.
    _require(name and '"' not in name and "`" not in name and "\n" not in name,
             f"invalid entity name {name!r}")
    _require(bool(_ENTITY_RE.match(name)), f"invalid entity name {name!r}")
    return name


def require_int(value, label: str, lo: int, hi: int) -> int:
    try:
        iv = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{label}: not an integer: {value!r}")
    _require(lo <= iv <= hi, f"{label}: {iv} out of range [{lo},{hi}]")
    return iv


def require_fmt(code: str) -> str:
    _require(bool(_FMT_RE.match(code or "")), f"invalid format code {code!r}")
    return code


def align_up(value: int, multiple: int) -> int:
    """Round ``value`` up to the next multiple (used for Jetson stride=256)."""
    if multiple <= 0:
        return value
    rem = value % multiple
    return value if rem == 0 else value + (multiple - rem)


def previewable_formats(list_formats_stdout: str) -> List[dict]:
    """Best-effort parse of ``v4l2-ctl --list-formats-ext`` output.

    Returns a list of {format, width, height, fps: [...]} entries.  On any
    unexpected shape it degrades gracefully to whatever it could extract.
    """
    results: List[dict] = []
    cur_fmt = None
    cur_size = None
    fmt_re = re.compile(r"^\s*\[\d+\]:\s*'([A-Za-z0-9 ]+?)'")
    size_re = re.compile(r"Size:\s*(?:Discrete|Stepwise|Continuous)?\s*(\d+)x(\d+)")
    fps_re = re.compile(r"\(([\d.]+)\s*fps\)")
    for line in (list_formats_stdout or "").splitlines():
        m = fmt_re.search(line)
        if m:
            cur_fmt = m.group(1).strip()
            continue
        m = size_re.search(line)
        if m and cur_fmt:
            cur_size = {"format": cur_fmt, "width": int(m.group(1)), "height": int(m.group(2)), "fps": []}
            results.append(cur_size)
            continue
        m = fps_re.search(line)
        if m and cur_size is not None:
            try:
                cur_size["fps"].append(float(m.group(1)))
            except ValueError:
                pass
    return results
