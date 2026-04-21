"""Detect display session type for follow-screen routing."""

from __future__ import annotations

import os


def is_wayland_session() -> bool:
    if os.environ.get("WAYLAND_DISPLAY"):
        return True
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
