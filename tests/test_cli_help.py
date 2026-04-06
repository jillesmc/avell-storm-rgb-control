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
