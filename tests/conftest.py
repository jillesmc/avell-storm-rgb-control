"""Keep every test away from the user's real saved device state."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolated_xdg_config(tmp_path_factory, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path_factory.mktemp("xdg")))


@pytest.fixture(autouse=True)
def _no_real_screen_capture(monkeypatch) -> None:
    """No test may open a real X11 capture or the Wayland portal picker (ScreenFrameHub)."""
    try:
        import app.core.screen_hub  # noqa: F401
    except ImportError:  # PySide6 missing: GUI code is not under test
        return
    def idle_frames(stop, **region):
        stop.wait()  # a capture that never produces a frame and ends only when stopped
        return
        yield  # pragma: no cover

    monkeypatch.setattr("app.core.screen_hub._default_frames", idle_frames)
