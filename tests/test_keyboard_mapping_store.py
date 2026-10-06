from pathlib import Path

from app.ui.adapters import keyboard_mapping_store as store


def test_roundtrip_device_overrides_v2(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / "keyboard_mapping_overrides.json"
    monkeypatch.setattr(store, "_config_path", lambda: p)

    store.save_device_mapping("dev-1", "abnt2_laptop_21", {"esc": (1, 2), "f1": (3, 4)})
    assert store.load_device_profile_id("dev-1", "legacy_builtin") == "abnt2_laptop_21"
    assert store.load_device_overrides("dev-1") == {"esc": (1, 2), "f1": (3, 4)}


def test_load_filters_invalid_cells(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / "keyboard_mapping_overrides.json"
    monkeypatch.setattr(store, "_config_path", lambda: p)
    p.write_text(
        '{"schema_version":2,"devices":{"dev-1":{"profileId":"legacy_builtin",'
        '"overrides":{"ok":[0,0],"bad_row":[99,1],"bad_col":[1,99]}}}}',
        encoding="utf-8",
    )

    got = store.load_device_overrides("dev-1")
    assert got == {"ok": (0, 0)}


def test_v1_schema_ignored(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / "keyboard_mapping_overrides.json"
    monkeypatch.setattr(store, "_config_path", lambda: p)
    p.write_text(
        '{"schema_version":1,"devices":{"dev-1":{"esc":[0,0]}}}',
        encoding="utf-8",
    )

    assert store.load_device_overrides("dev-1") == {}
    assert store.load_device_profile_id("dev-1", "legacy_builtin") == "legacy_builtin"


def test_clear_device_mapping(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / "keyboard_mapping_overrides.json"
    monkeypatch.setattr(store, "_config_path", lambda: p)
    store.save_device_mapping("dev-1", "abnt2_laptop_21", {"esc": (0, 0)})
    store.clear_device_mapping("dev-1", "legacy_builtin")
    assert store.load_device_profile_id("dev-1", "x") == "legacy_builtin"
    assert store.load_device_overrides("dev-1") == {}
