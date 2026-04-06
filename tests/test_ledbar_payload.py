from avell_storm_rgb.domain.ledbar_colors import build_led_bar_effect_report


def test_led_bar_effect_report_matches_legacy_shape() -> None:
    # Legacy: [CMD_EFFECT, 0x22, effect, speed, brightness, num_colors, 0, 0]
    assert build_led_bar_effect_report(0x03, 5, 75, 2) == bytes(
        [0x08, 0x22, 0x03, 5, 75, 2, 0x00, 0x00]
    )
