from avell_storm_rgb.domain.anim_dsl import parse_rgb_triplet, run_animation_lines


def test_parse_rgb_triplet() -> None:
    assert parse_rgb_triplet("255,0,128") == (255, 0, 128)


def test_run_animation_apply_and_brightness() -> None:
    applied = []
    bright = []

    run_animation_lines(
        ["pos 0 0 255,0,0", "apply", "brightness 10"],
        on_apply=lambda m: applied.append(dict(m)),
        on_brightness=lambda b: bright.append(b),
        sleep=lambda _: None,
    )
    assert applied == [{(0, 0): (255, 0, 0)}]
    assert bright == [10]
