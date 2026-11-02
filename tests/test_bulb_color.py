import pytest

from avell_storm_rgb.domain.bulb_color import (
    BulbStatus,
    average_rgb,
    changed_enough,
    colour_data_v2_to_rgb,
    device_to_percent,
    percent_to_device,
    rgb_to_colour_data_v2,
    status_from_dps,
)


@pytest.mark.parametrize(("percent", "device"), [(1, 10), (40, 400), (100, 1000)])
def test_percent_to_device_maps_type_b_range(percent: int, device: int) -> None:
    assert percent_to_device(percent) == device


@pytest.mark.parametrize("percent", [0, 101, -1])
def test_percent_to_device_rejects_out_of_range(percent: int) -> None:
    with pytest.raises(ValueError):
        percent_to_device(percent)


@pytest.mark.parametrize(("device", "percent"), [(10, 1), (400, 40), (1000, 100), (0, 0)])
def test_device_to_percent_is_the_inverse(device: int, percent: int) -> None:
    assert device_to_percent(device) == percent


def test_rgb_to_colour_data_v2_round_trip() -> None:
    value = rgb_to_colour_data_v2((255, 136, 0))
    assert value == "002003e803e8"
    back = colour_data_v2_to_rgb(value)
    assert all(abs(a - b) <= 2 for a, b in zip(back, (255, 136, 0)))


def test_rgb_to_colour_data_v2_clamps_black_to_one_percent() -> None:
    value = rgb_to_colour_data_v2((0, 0, 0))
    assert value == "00000000000a"
    assert int(value[8:12], 16) == 10


def test_average_rgb_averages_each_channel() -> None:
    assert average_rgb([(255, 0, 0), (0, 0, 255)]) == (128, 0, 128)


def test_average_rgb_rejects_an_empty_iterable() -> None:
    with pytest.raises(ValueError):
        average_rgb([])


def test_status_from_dps_reads_scene_mode() -> None:
    status = status_from_dps({"20": True, "21": "scene", "22": 500})
    assert status == BulbStatus(
        on=True, mode="scene", brightness=50, temperature=None, rgb=None
    )


def test_status_from_dps_reads_colour_mode() -> None:
    status = status_from_dps({"21": "colour", "24": "000003e803e8"})
    assert status.on is False
    assert status.mode == "colour"
    assert status.rgb == (255, 0, 0)
    assert status.brightness == 100
    assert status.temperature is None


def test_status_from_dps_reads_white_temperature() -> None:
    status = status_from_dps({"20": True, "21": "white", "22": 1000, "23": 0})
    assert status.on is True
    assert status.mode == "white"
    assert status.brightness == 100
    assert status.temperature == 0
    assert status.rgb is None


def test_changed_enough_uses_the_eight_step_threshold() -> None:
    assert changed_enough((10, 10, 10), (17, 10, 10)) is False
    assert changed_enough((10, 10, 10), (18, 10, 10)) is True
