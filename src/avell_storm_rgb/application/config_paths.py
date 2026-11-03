"""Where the app keeps its config (``state.json``, bulb inventory, UI settings).

``AVELL_STORM_RGB_CONFIG_DIR`` points a development instance at its own directory so it
never touches the installed (production) app's config. ``XDG_CONFIG_HOME`` is not used
for that: it also moves the KDE theme config, so the dev GUI would lose the system theme.
"""

from __future__ import annotations

import os
from pathlib import Path

CONFIG_DIR_ENV = "AVELL_STORM_RGB_CONFIG_DIR"


def config_dir_override() -> Path | None:
    raw = os.environ.get(CONFIG_DIR_ENV, "").strip()
    return Path(raw).expanduser() if raw else None


def app_config_dir() -> Path:
    """``$AVELL_STORM_RGB_CONFIG_DIR``, else ``$XDG_CONFIG_HOME/avell-storm-rgb`` (``~/.config``)."""
    override = config_dir_override()
    if override is not None:
        return override
    base = os.environ.get("XDG_CONFIG_HOME", "")
    root = Path(base) if base and os.path.isabs(base) else Path.home() / ".config"
    return root / "avell-storm-rgb"
