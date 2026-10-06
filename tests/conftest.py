"""Keep every test away from the user's real saved device state."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolated_xdg_config(tmp_path_factory, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path_factory.mktemp("xdg")))
