"""KeyboardBackend.effectSupports mirrors EFFECT_KWARGS."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.ui.adapters.keyboard_backend import KeyboardBackend
from app.core.usb_worker import UsbWorker


def test_effect_supports_wave_has_direction_not_reactive() -> None:
    w = MagicMock(spec=UsbWorker)
    kb = KeyboardBackend(w)
    assert kb.effectSupports("wave", "direction") is True
    assert kb.effectSupports("wave", "reactive") is False
    assert kb.effectSupports("wave", "color") is False


def test_effect_supports_rainbow_brightness_only_speed() -> None:
    w = MagicMock(spec=UsbWorker)
    kb = KeyboardBackend(w)
    assert kb.effectSupports("rainbow", "brightness") is True
    assert kb.effectSupports("rainbow", "speed") is False
    assert kb.effectSupports("rainbow", "save") is True
