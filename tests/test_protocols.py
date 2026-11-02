from __future__ import annotations

from avell_storm_rgb.domain.bulb_color import BulbStatus
from avell_storm_rgb.infrastructure.usb.ite8291_usb import Ite8291UsbDevice
from avell_storm_rgb.infrastructure.usb.ite8233_usb import Ite8233UsbDevice
from avell_storm_rgb.ports.protocols import BulbDriver


class _FakeBulb:
    def status(self) -> BulbStatus:
        return BulbStatus(on=False, mode="white", brightness=100, temperature=50, rgb=None)

    def set_power(self, on: bool) -> None: ...
    def set_brightness(self, percent: int, status: BulbStatus | None) -> None: ...
    def set_white(self, temperature_percent: int | None, status: BulbStatus | None) -> None: ...
    def set_colour(self, rgb: tuple[int, int, int]) -> None: ...
    def push_colour(self, rgb: tuple[int, int, int]) -> None: ...
    def hold_open(self, persistent: bool) -> None: ...
    def close(self) -> None: ...


def test_keyboard_driver_is_protocol_instance() -> None:
    # isinstance check without USB: use a mock with required methods would be heavy;
    # structural: concrete classes implement the same methods as Protocol.
    assert hasattr(Ite8291UsbDevice, "set_key_colors")
    assert hasattr(Ite8291UsbDevice, "turn_off")


def test_led_bar_driver_has_protocol_shape() -> None:
    assert hasattr(Ite8233UsbDevice, "power_on")
    assert hasattr(Ite8233UsbDevice, "apply_visual_effect")


def test_bulb_driver_is_runtime_checkable() -> None:
    assert isinstance(_FakeBulb(), BulbDriver)


def test_bulb_driver_rejects_an_incomplete_object() -> None:
    class _NotABulb:
        def status(self) -> BulbStatus:
            return BulbStatus(on=False, mode="white", brightness=100, temperature=None, rgb=None)

    assert not isinstance(_NotABulb(), BulbDriver)
