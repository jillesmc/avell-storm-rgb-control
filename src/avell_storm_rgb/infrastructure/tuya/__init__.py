"""Tuya LAN adapter — the only package that imports ``tinytuya`` (ADR-001).

``tinytuya`` is imported lazily inside the functions of
:mod:`avell_storm_rgb.infrastructure.tuya.bulb`, so ``import avell_storm_rgb``
and the CLI keep working without the optional ``tuya`` extra.
"""

from __future__ import annotations

from avell_storm_rgb.infrastructure.tuya.bulb import (
    BulbError,
    BulbUnreachable,
    Discovered,
    KeyRejected,
    TuyaBulb,
    discover_bulb,
)

__all__ = [
    "BulbError",
    "BulbUnreachable",
    "Discovered",
    "KeyRejected",
    "TuyaBulb",
    "discover_bulb",
]
