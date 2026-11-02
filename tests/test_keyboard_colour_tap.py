"""_ColourTap: keyboard colours reported only after successful solid/per-key writes (UT-081–UT-085)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtCore")

from app.ui.adapters.keyboard_backend import _ColourTap
from backend_fakes import FakeKeyboard


def _tap(kb):
    seen: list = []
    return _ColourTap(kb, seen.append), seen


def test_ut081_set_color_reports_after_success() -> None:
    tap, seen = _tap(FakeKeyboard())
    tap.set_color((0, 0, 255))
    assert seen == [(0, 0, 255)]


def test_ut081_raising_driver_reports_nothing() -> None:
    tap, seen = _tap(FakeKeyboard(fail_on=frozenset({"set_color"})))
    with pytest.raises(RuntimeError):
        tap.set_color((0, 0, 255))
    assert seen == []


def test_ut082_per_key_average() -> None:
    tap, seen = _tap(FakeKeyboard())
    tap.set_key_colors({(0, 0): (255, 0, 0), (0, 1): (0, 0, 255)})
    assert seen == [(128, 0, 128)]


def test_ut084_ut085_effect_and_off_report_nothing() -> None:
    kb = FakeKeyboard()
    tap, seen = _tap(kb)
    tap.set_effect([1, 2, 3, 4, 5, 6])
    tap.turn_off()
    assert seen == []
    assert kb.calls[0][0] == "set_effect"  # forwarded to the real driver


def test_tap_forwards_attributes() -> None:
    kb = FakeKeyboard()
    tap, _ = _tap(kb)
    assert tap.get_fw_version() == (1, 2, 3, 4)
    tap.close()
    assert ("close",) in kb.calls
