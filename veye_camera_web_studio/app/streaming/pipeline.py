"""GStreamer pipeline assembly.

Joins Stage 1 (provider capture/convert) and Stage 2 (transport encode/mux/sink)
into a single ``gst-launch-1.0`` argv list.  We build argv (never a shell string)
so there is no shell to inject into; every dynamic value is already validated.
"""
from __future__ import annotations

from typing import List

from .profile import StreamProfile
from .providers.base import StreamProvider
from .transports.base import StreamTransport


def build_gst_argv(profile: StreamProfile, provider: StreamProvider, transport: StreamTransport) -> List[str]:
    tokens: List[str] = ["gst-launch-1.0", "-e"]
    tokens += [
        "v4l2src",
        f"device={profile.video_node}",
        f"io-mode={provider.io_mode(profile)}",
        "!",
        profile.input_caps(),
        "!",
    ]
    tokens += provider.capture_to_encoder_tokens(profile)
    tokens += ["!"]
    tokens += transport.sink_tokens(profile)
    return tokens


def argv_to_str(argv: List[str]) -> str:
    """Human-readable single-line form for logs / dry_run previews."""
    return " ".join(a if (" " not in a and a != "") else f'"{a}"' for a in argv)
