"""BulbWorker: per-bulb queues, GUI-thread results, one driver per bulb (UT-060–UT-064)."""

from __future__ import annotations

import threading

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QObject, QThread, Qt, Slot
from PySide6.QtWidgets import QApplication

from app.core.bulb_worker import BulbWorker
from app.core.usb_worker import UsbWorker
from avell_storm_rgb.application.bulb_facade import BulbUnreachable, KeyRejected
from avell_storm_rgb.application.bulb_inventory import BulbFailure
from backend_fakes import FakeBulb, drain_bulbs


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    FakeBulb.live_connections = 0
    return QApplication.instance() or QApplication([])


class Sink(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.done: list = []
        self.failed: list[str] = []
        self.threads: list = []

    @Slot(str, object)
    def on_done(self, bulb_id, result) -> None:
        self.threads.append(QThread.currentThread())
        self.done.append((bulb_id, result))

    @Slot(str)
    def on_failed(self, text) -> None:
        self.failed.append(text)


def _worker(opener, **kw):
    w = BulbWorker(opener, **kw)
    sink = Sink()
    w.opDone.connect(sink.on_done, Qt.ConnectionType.QueuedConnection)
    w.opFailed.connect(sink.on_failed, Qt.ConnectionType.QueuedConnection)
    return w, sink


def test_ut060_bulbs_run_in_parallel(app) -> None:
    w, sink = _worker(lambda _id: FakeBulb())
    gate = threading.Event()
    w.submit("a", lambda d: gate.wait(5) and "a")
    w.submit("b", lambda d: "b").result(timeout=5)
    assert not gate.is_set()  # A still blocked while B completed
    gate.set()
    drain_bulbs(w)
    assert [r for _, r in sink.done] == ["b", "a"]
    w.shutdown(wait=True)


def test_ut061_fifo_per_bulb(app) -> None:
    w, sink = _worker(lambda _id: FakeBulb())
    for i in range(5):
        w.submit("a", lambda d, i=i: i)
    drain_bulbs(w)
    assert [r for _, r in sink.done] == [0, 1, 2, 3, 4]
    w.shutdown(wait=True)


def test_ut062_bulb_threads_never_usb(app) -> None:
    usb = UsbWorker()
    started: list = []
    usb.opStarted.connect(lambda: started.append(1))
    w, _sink = _worker(lambda _id: FakeBulb())
    names: list[str] = []
    w.submit("a", lambda d: names.append(threading.current_thread().name))
    w.submit("b", lambda d: names.append(threading.current_thread().name))
    drain_bulbs(w)
    assert len(names) == 2 and all(n.startswith("bulb") for n in names)
    assert not any(n.startswith("usb") for n in names)
    assert started == []
    w.shutdown(wait=True)
    usb.shutdown(wait=True)


def test_ut063_op_done_reaches_gui_thread(app) -> None:
    w, sink = _worker(lambda _id: FakeBulb())
    w.submit("a", lambda d: d.status())
    drain_bulbs(w)
    assert sink.threads == [app.thread()]
    w.shutdown(wait=True)


def test_ut064_held_driver_is_reused(app) -> None:
    made: list[FakeBulb] = []

    def opener(_id):
        made.append(FakeBulb(reject_second_connection=True))
        return made[-1]

    w, sink = _worker(opener)
    w.set_hold_open("a", True)
    w.submit("a", lambda d: d.set_power(True))
    w.submit("a", lambda d: d.set_colour((1, 2, 3)))
    w.submit("a", lambda d: d.push_colour((4, 5, 6)))
    drain_bulbs(w)
    assert len(made) == 1
    assert made[0].names() == ["hold_open", "set_power", "set_colour", "push_colour"]
    w.set_hold_open("a", False)
    drain_bulbs(w)
    assert made[0].closed
    w.shutdown(wait=True)


def test_driver_closed_after_each_unheld_task(app) -> None:
    made: list[FakeBulb] = []
    w, _sink = _worker(lambda _id: made.append(FakeBulb()) or made[-1])
    w.submit("a", lambda d: None)
    w.submit("a", lambda d: None)
    drain_bulbs(w)
    assert len(made) == 2 and all(b.closed for b in made)
    w.shutdown(wait=True)


@pytest.mark.parametrize(
    ("exc", "row", "banner"),
    [
        (
            BulbUnreachable("Sala"),
            "Sala is not reachable on the network",
            "Sala is not reachable on the network. Check that it is powered; discovery uses UDP 6666/6667.",
        ),
        (
            KeyRejected("local key or protocol rejected"),
            "Sala rejected the local key or protocol — re-import devices.json",
            "Sala rejected the local key or protocol — re-import devices.json",
        ),
    ],
)
def test_failures_become_texts(app, exc, row, banner) -> None:
    def opener(_id):
        raise exc

    w, sink = _worker(opener, name_of=lambda _id: "Sala")
    w.submit("a", lambda d: d.status())
    drain_bulbs(w)
    (_, failure), = sink.done
    assert isinstance(failure, BulbFailure) and failure.reason == row
    assert sink.failed == [banner]
    w.shutdown(wait=True)
