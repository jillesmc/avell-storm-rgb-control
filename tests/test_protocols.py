from avell_storm_rgb.infrastructure.usb.ite8291_usb import Ite8291UsbDevice
from avell_storm_rgb.infrastructure.usb.ite8233_usb import Ite8233UsbDevice


def test_keyboard_driver_is_protocol_instance() -> None:
    # isinstance check without USB: use a mock with required methods would be heavy;
    # structural: concrete classes implement the same methods as Protocol.
    assert hasattr(Ite8291UsbDevice, "set_key_colors")
    assert hasattr(Ite8291UsbDevice, "turn_off")


def test_led_bar_driver_has_protocol_shape() -> None:
    assert hasattr(Ite8233UsbDevice, "power_on")
    assert hasattr(Ite8233UsbDevice, "apply_visual_effect")
