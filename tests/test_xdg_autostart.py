"""XDG autostart desktop entry helpers."""

from __future__ import annotations

import shlex

import pytest

from app.core import xdg_autostart as autostart


@pytest.fixture
def isolated_xdg_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    yield tmp_path


def test_autostart_disabled_when_file_missing(isolated_xdg_config) -> None:
    assert autostart.is_enabled() is False


def test_enable_writes_desktop_file_with_background_flag(isolated_xdg_config) -> None:
    autostart.enable(exec_prefix="/usr/bin/avell-storm-rgb-gui")
    path = autostart.autostart_file_path()
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "Type=Application" in text
    assert "Name=Avell Storm RGB" in text
    exec_line = next(line for line in text.splitlines() if line.startswith("Exec="))
    parts = shlex.split(exec_line[len("Exec=") :])
    assert parts[-1] == autostart.BACKGROUND_ARG
    assert parts[0] == "/usr/bin/avell-storm-rgb-gui"
    assert autostart.is_enabled() is True


def test_disable_removes_desktop_file(isolated_xdg_config) -> None:
    autostart.enable(exec_prefix="/usr/bin/avell-storm-rgb-gui")
    autostart.disable()
    assert autostart.is_enabled() is False
    assert not autostart.autostart_file_path().exists()


def test_capture_launch_command_strips_gui_flags(monkeypatch) -> None:
    monkeypatch.setattr(
        autostart.sys,
        "argv",
        [
            "/venv/bin/python",
            "-m",
            "app.main",
            "--verbose",
            autostart.BACKGROUND_ARG,
        ],
    )
    cmd = autostart.capture_launch_command()
    parts = shlex.split(cmd)
    assert parts == ["/venv/bin/python", "-m", "app.main"]


def test_capture_launch_command_falls_back_when_argv_is_python_c(monkeypatch) -> None:
    monkeypatch.setattr(autostart.sys, "argv", ["-c"])
    monkeypatch.setattr(autostart.sys, "executable", "/usr/bin/python3")
    cmd = autostart.capture_launch_command()
    parts = shlex.split(cmd)
    assert parts == ["/usr/bin/python3", "-m", "app.main"]


def test_enable_preserves_existing_exec_prefix_on_update(isolated_xdg_config) -> None:
    autostart.enable(exec_prefix="/opt/custom/avell-storm-rgb-gui")
    path = autostart.autostart_file_path()
    autostart.enable()
    exec_prefix = autostart.parse_exec_prefix(path)
    assert exec_prefix == "/opt/custom/avell-storm-rgb-gui"
