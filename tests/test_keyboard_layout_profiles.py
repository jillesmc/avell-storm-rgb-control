from avell_storm_rgb.domain.keyboard_layouts import resolve_usb_default_profile
from avell_storm_rgb.domain.per_key_grid import active_profile_id, set_active_profile


def test_usb_default_abnt2() -> None:
    assert resolve_usb_default_profile(0x6006) == "abnt2_laptop_21"


def test_set_active_profile_switches_maps() -> None:
    set_active_profile("abnt2_laptop_21")
    assert active_profile_id() == "abnt2_laptop_21"
    set_active_profile("legacy_builtin")
    assert active_profile_id() == "legacy_builtin"
