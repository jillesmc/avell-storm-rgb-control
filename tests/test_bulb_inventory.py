import json
import os
import stat
from dataclasses import replace
from pathlib import Path

import pytest

from avell_storm_rgb.application.bulb_inventory import (
    AmbiguousTarget,
    BulbInventory,
    BulbRecord,
    ImportFileError,
    InventoryFileError,
    UnknownTarget,
    default_inventory_path,
    match_target,
    parse_tinytuya_devices,
)

FIXTURE = Path(__file__).parent / "fixtures" / "tinytuya_devices.json"


def _fixture_doc() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _fixture_records() -> list[BulbRecord]:
    records, _ = parse_tinytuya_devices(_fixture_doc())
    return records


# --- import parsing (UT-010, UT-013, UT-014, UT-015) -------------------------


def test_parse_tinytuya_devices_reads_the_wizard_fixture() -> None:
    records, skipped = parse_tinytuya_devices(_fixture_doc())

    assert skipped == []
    assert [record.name for record in records] == ["Quarto", "Escritório", "Sala"]
    assert all(record.mac == record.mac.lower() for record in records)
    assert records[0].mac == "10:d5:61:00:00:01"
    assert records[0].protocol == "3.3"
    assert records[1].protocol == "3.3"  # blank version defaults
    assert records[0].last_ip == "192.168.0.21"
    assert records[2].last_ip is None


@pytest.mark.parametrize("doc", ["{}", {}, 42])
def test_parse_tinytuya_devices_rejects_a_non_list(doc: object) -> None:
    with pytest.raises(ImportFileError) as exc:
        parse_tinytuya_devices(doc)
    assert exc.value.reason == "expected a list of devices"


def test_parse_tinytuya_devices_rejects_invalid_json() -> None:
    with pytest.raises(ImportFileError) as exc:
        parse_tinytuya_devices("{")
    assert exc.value.reason == "invalid JSON at line 1 column 2"


def test_parse_tinytuya_devices_skips_an_entry_without_a_key() -> None:
    records, skipped = parse_tinytuya_devices(
        [{"id": "fictional-id-1", "name": "Sem chave", "category": "dj"}]
    )
    assert records == []
    assert [(entry.id, entry.reason) for entry in skipped] == [("fictional-id-1", "no local key")]


def test_parse_tinytuya_devices_skips_a_non_bulb() -> None:
    records, skipped = parse_tinytuya_devices(
        [{"id": "fictional-id-2", "name": "Tomada", "key": "fictional", "category": "cz"}]
    )
    assert records == []
    assert skipped[0].reason == "not a bulb (category cz)"


def test_parse_tinytuya_devices_skips_a_missing_category() -> None:
    records, skipped = parse_tinytuya_devices(
        [{"id": "fictional-id-3", "name": "Sem categoria", "key": "fictional"}]
    )
    assert records == []
    assert skipped[0].reason == "missing category"


# --- inventory file (UT-011, UT-012, UT-016, UT-070) -------------------------


def test_upsert_on_an_empty_file_writes_version_one(tmp_path: Path) -> None:
    path = tmp_path / "tuya_devices.json"
    records = _fixture_records()

    report = BulbInventory(path).upsert(records)

    assert [result.status for result in report.results] == ["added", "added", "added"]
    assert report.imported == 3
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["version"] == 1
    assert [entry["id"] for entry in doc["devices"]] == [record.id for record in records]


def test_upsert_updates_a_changed_key_and_keeps_the_order(tmp_path: Path) -> None:
    inventory = BulbInventory(tmp_path / "tuya_devices.json")
    records = _fixture_records()
    inventory.upsert(records)

    changed = replace(records[2], key="fictional-replacement-key")
    report = inventory.upsert([records[0], records[1], changed])

    by_id = {result.id: (result.status, result.reason) for result in report.results}
    assert by_id[records[0].id] == ("unchanged", None)
    assert by_id[records[1].id] == ("unchanged", None)
    assert by_id[records[2].id] == ("updated", "key changed")

    stored = inventory.load()
    assert [record.id for record in stored] == [record.id for record in records]
    assert stored[2].key == "fictional-replacement-key"


def test_upsert_joins_every_changed_field_reason(tmp_path: Path) -> None:
    inventory = BulbInventory(tmp_path / "tuya_devices.json")
    records = _fixture_records()
    inventory.upsert(records)

    changed = replace(
        records[0],
        key="fictional-key",
        name="Quarto novo",
        mac="aa:bb:cc:dd:ee:ff",
        protocol="3.4",
    )
    report = inventory.upsert([changed])

    assert report.results[0].reason == "key changed, name changed, mac changed, protocol changed"


def test_upsert_of_an_empty_list_leaves_the_file_alone(tmp_path: Path) -> None:
    path = tmp_path / "tuya_devices.json"
    inventory = BulbInventory(path)

    assert inventory.upsert([]).imported == 0
    assert not path.exists()

    inventory.upsert(_fixture_records()[:1])
    before = path.read_bytes()
    assert inventory.upsert([]).imported == 0
    assert path.read_bytes() == before


def test_load_missing_file_returns_an_empty_list(tmp_path: Path) -> None:
    assert BulbInventory(tmp_path / "missing.json").load() == []


def test_load_invalid_json_raises_inventory_file_error(tmp_path: Path) -> None:
    path = tmp_path / "tuya_devices.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(InventoryFileError) as exc:
        BulbInventory(path).load()
    assert exc.value.reason == "invalid JSON at line 1 column 2"


def test_load_unknown_version_raises_inventory_file_error(tmp_path: Path) -> None:
    path = tmp_path / "tuya_devices.json"
    path.write_text(json.dumps({"version": 2, "devices": []}), encoding="utf-8")
    with pytest.raises(InventoryFileError) as exc:
        BulbInventory(path).load()
    assert "unsupported version 2" == exc.value.reason


def test_remove_deletes_only_the_named_record(tmp_path: Path) -> None:
    inventory = BulbInventory(tmp_path / "tuya_devices.json")
    records = _fixture_records()
    inventory.upsert(records)

    removed = inventory.remove(records[1].id)

    assert removed == records[1]
    assert [record.id for record in inventory.load()] == [records[0].id, records[2].id]


def test_remove_unknown_id_returns_none(tmp_path: Path) -> None:
    inventory = BulbInventory(tmp_path / "tuya_devices.json")
    inventory.upsert(_fixture_records())
    assert inventory.remove("fictional-unknown") is None
    assert len(inventory.load()) == 3


def test_set_last_ip_updates_the_matching_record(tmp_path: Path) -> None:
    inventory = BulbInventory(tmp_path / "tuya_devices.json")
    records = _fixture_records()
    inventory.upsert(records)

    inventory.set_last_ip(records[2].id, "192.168.0.23")

    assert inventory.load()[2].last_ip == "192.168.0.23"


def test_new_inventory_file_is_mode_0600(tmp_path: Path) -> None:
    path = tmp_path / "tuya_devices.json"
    BulbInventory(path).upsert(_fixture_records())
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_save_over_an_existing_0600_file_keeps_mode_0600(tmp_path: Path) -> None:
    path = tmp_path / "tuya_devices.json"
    records = _fixture_records()
    inventory = BulbInventory(path)
    inventory.save(records)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600

    inventory.save([replace(records[0], key="fictional-other-key")])

    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_save_tightens_a_looser_existing_file_to_0600(tmp_path: Path) -> None:
    path = tmp_path / "tuya_devices.json"
    path.write_text("{}", encoding="utf-8")
    os.chmod(path, 0o644)

    BulbInventory(path).save(_fixture_records())

    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_bulb_record_repr_never_contains_the_key() -> None:
    record = BulbRecord(
        id="fictional-id",
        name="Luz",
        key="KEY-SENTINEL-123",
        mac="aa:bb:cc:dd:ee:ff",
    )
    assert "KEY-SENTINEL-123" not in repr(record)
    assert "KEY-SENTINEL-123" not in str(record)


# --- target matching (UT-017, UT-018, UT-019) -------------------------------


def test_match_target_accepts_all_name_and_id() -> None:
    records = _fixture_records()

    assert match_target(records, "all") == records
    assert match_target(records, "escritorio") == [records[1]]
    assert match_target(records, "ESCRITÓRIO") == [records[1]]
    assert match_target(records, records[0].id) == [records[0]]


def test_match_target_unknown_name_lists_the_known_bulbs() -> None:
    with pytest.raises(UnknownTarget) as exc:
        match_target(_fixture_records(), "cozinha")
    assert exc.value.known == ("Quarto", "Escritório", "Sala")
    assert "Quarto, Escritório, Sala" in str(exc.value)


def test_match_target_ambiguous_name_lists_both_ids() -> None:
    records = [
        BulbRecord(id="fictional-id-a", name="Luz", key="a", mac="aa:bb:cc:dd:ee:01"),
        BulbRecord(id="fictional-id-b", name="Luz", key="b", mac="aa:bb:cc:dd:ee:02"),
    ]
    with pytest.raises(AmbiguousTarget) as exc:
        match_target(records, "luz")
    assert exc.value.ids == ("fictional-id-a", "fictional-id-b")
    assert "fictional-id-a, fictional-id-b" in str(exc.value)


def test_default_inventory_path_uses_xdg_config_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert default_inventory_path() == tmp_path / "avell-storm-rgb" / "tuya_devices.json"
