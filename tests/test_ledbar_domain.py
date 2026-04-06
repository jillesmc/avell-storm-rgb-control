import pytest

from avell_storm_rgb.domain.ledbar_colors import parse_color, parse_palette


def test_parse_named_color() -> None:
    assert parse_color("red") == (255, 0, 0)


def test_parse_hex_color() -> None:
    assert parse_color("#ff5500") == (255, 85, 0)


def test_parse_palette_preset() -> None:
    p = parse_palette("fire")
    assert len(p) == 4
    assert p[0] == (255, 0, 0)


def test_parse_unknown_color() -> None:
    with pytest.raises(ValueError):
        parse_color("notacolor")
