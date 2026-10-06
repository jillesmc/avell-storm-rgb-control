"""XDG autostart desktop entry for the GUI (Linux session login)."""

from __future__ import annotations

import os
import shlex
import sys
from configparser import ConfigParser
from pathlib import Path

AUTOSTART_FILENAME = "avell-storm-rgb-gui.desktop"
BACKGROUND_ARG = "--background"
APP_NAME = "Avell Storm RGB"


def config_home() -> Path:
    raw = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".config"


def autostart_dir() -> Path:
    return config_home() / "autostart"


def autostart_file_path() -> Path:
    return autostart_dir() / AUTOSTART_FILENAME


def is_enabled() -> bool:
    return autostart_file_path().is_file()


def capture_launch_command(argv: list[str] | None = None) -> str:
    """Build a shell-safe Exec= prefix from the current process argv (without GUI flags)."""
    raw = list(argv if argv is not None else sys.argv)
    skip_next = False
    filtered: list[str] = []
    for arg in raw:
        if skip_next:
            skip_next = False
            continue
        if arg in ("-v", "--verbose", "--debug", BACKGROUND_ARG):
            continue
        if arg == "--":
            break
        filtered.append(arg)
    if not filtered or filtered[0] in ("-c", "-m"):
        filtered = [sys.executable, "-m", "app.main"]
    return " ".join(shlex.quote(part) for part in filtered)


def _read_existing_exec_prefix(path: Path) -> str | None:
    if not path.is_file():
        return None
    parser = ConfigParser()
    parser.read(path, encoding="utf-8")
    if not parser.has_section("Desktop Entry"):
        return None
    exec_line = parser.get("Desktop Entry", "Exec", fallback="").strip()
    if not exec_line:
        return None
    parts = shlex.split(exec_line)
    if parts and parts[-1] == BACKGROUND_ARG:
        parts = parts[:-1]
    if not parts:
        return None
    return " ".join(shlex.quote(part) for part in parts)


def _desktop_entry_text(exec_prefix: str) -> str:
    exec_line = f"{exec_prefix} {BACKGROUND_ARG}"
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        f"Name={APP_NAME}",
        "Comment=Control ITE keyboard RGB and LED bar (USB)",
        f"Exec={exec_line}",
        "Icon=adjustrgb",
        "Terminal=false",
        "Categories=Settings;Utility;",
        "X-GNOME-Autostart-enabled=true",
        "StartupNotify=false",
        "",
    ]
    return "\n".join(lines)


def enable(*, exec_prefix: str | None = None) -> None:
    """Write or update the autostart desktop file."""
    path = autostart_file_path()
    prefix = exec_prefix
    if prefix is None:
        prefix = _read_existing_exec_prefix(path) or capture_launch_command()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_desktop_entry_text(prefix), encoding="utf-8")


def disable() -> None:
    """Remove the autostart desktop file if present."""
    path = autostart_file_path()
    if path.is_file():
        path.unlink()


def parse_exec_prefix(path: Path) -> str | None:
    """Parse Exec= from an existing desktop file (test helper / introspection)."""
    return _read_existing_exec_prefix(path)
