"""BulbFollower: rate, threshold, power gate, one held driver (UT-083, UT-086, UT-095, UT-096, UT-101)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtWidgets import QApplication

from app.core.bulb_worker import BulbWorker
from app.ui.adapters.bulb_follow import STATUS_READ_MS, TICK_MS, BulbFollower
from backend_fakes import FakeBulb, drain_bulbs


@pytest.fixture
def rig(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    QApplication.instance() or QApplication([])
    FakeBulb.live_connections = 0
    made: list[FakeBulb] = []

    def opener(_id):
        made.append(FakeBulb(reject_second_connection=True))
        return made[-1]

    worker = BulbWorker(opener)
    state = {"on": True, "reads": 0}

    def read(_id):
        state["reads"] += 1

    follower = BulbFollower(worker, power_on=lambda _id: state["on"], read_status=read)
    yield worker, follower, made, state
    follower.stop_all()
    worker.shutdown(wait=True)


def _pushes(made) -> list:
    return [c[1] for b in made for c in b.calls if c[0] == "push_colour"]


def _tick(worker, follower, bulb_id="a") -> None:
    follower._tick(bulb_id)
    drain_bulbs(worker)


def test_intervals() -> None:
    assert TICK_MS == 250 and STATUS_READ_MS == 5_000  # 4 pushes/s max; 5 s read while following


def test_ut083_latest_colour_once_per_tick(rig) -> None:
    worker, follower, made, _ = rig
    follower.set_source("a", "keyboard")
    colours = [(i * 12, 0, 0) for i in range(20)]
    for i, c in enumerate(colours):  # 20 colours in "1 s" = 4 ticks
        follower.feed("keyboard", c)
        if i % 5 == 4:
            _tick(worker, follower)
    pushes = _pushes(made)
    assert len(pushes) == 4
    assert pushes[-1] == colours[-1]
    assert len(made) == 1  # one held driver, never a second connection


def test_ut086_threshold(rig) -> None:
    worker, follower, made, _ = rig
    follower.set_source("a", "keyboard")
    follower.feed("keyboard", (100, 100, 100))
    _tick(worker, follower)
    follower.feed("keyboard", (107, 100, 100))
    _tick(worker, follower)
    follower.feed("keyboard", (108, 100, 100))
    _tick(worker, follower)
    assert _pushes(made) == [(100, 100, 100), (108, 100, 100)]


def test_ut095_ut101_power_off_or_unknown_never_pushes(rig) -> None:
    worker, follower, made, state = rig
    state["on"] = False  # off, or never read (power_on is False for unknown)
    follower.set_source("a", "keyboard")
    follower.feed("keyboard", (0, 0, 255))
    _tick(worker, follower)
    assert _pushes(made) == []
    state["on"] = True
    _tick(worker, follower)
    assert _pushes(made) == [(0, 0, 255)]


def test_ut096_status_read_runs_while_following(rig) -> None:
    worker, follower, made, state = rig
    follower.set_source("a", "keyboard")
    follower._following["a"].status.timeout.emit()
    assert state["reads"] == 1
    state["on"] = False  # the 5 s read saw the bulb switched off
    follower.feed("keyboard", (1, 200, 3))
    _tick(worker, follower)
    assert _pushes(made) == []


def test_other_source_ignored_and_none_releases(rig) -> None:
    worker, follower, made, _ = rig
    follower.set_source("a", "led_bar")
    follower.feed("keyboard", (0, 0, 255))
    _tick(worker, follower)
    assert _pushes(made) == []
    follower.set_source("a", "none")
    drain_bulbs(worker)
    assert made[0].closed and ("hold_open", False) in made[0].calls
