import subprocess
import sys


def test_cli_help_exits_zero() -> None:
    r = subprocess.run([sys.executable, "-m", "avell_storm_rgb.adapters.cli.main", "-h"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "avell-storm-rgb" in r.stdout or "Unified USB" in r.stdout


def test_device_list_help() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "avell_storm_rgb.adapters.cli.main", "device", "list", "-h"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0


def test_state_help_lists_show_and_restore() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "avell_storm_rgb.adapters.cli.main", "state", "-h"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert "show" in r.stdout and "restore" in r.stdout


BULB_VERBS = ("import", "list", "status", "on", "off", "toggle", "bright", "white", "color", "remove")


def test_main_help_lists_bulb_group() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "avell_storm_rgb.adapters.cli.main", "-h"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert "bulb" in r.stdout


def test_bulb_help_lists_every_verb() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "avell_storm_rgb.adapters.cli.main", "bulb", "-h"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    for verb in BULB_VERBS:
        assert verb in r.stdout
