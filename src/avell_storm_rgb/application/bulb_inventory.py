"""Private Tuya bulb inventory and tinytuya ``devices.json`` import.

The inventory file (``tuya_devices.json``) holds local keys, so it is written
atomically with mode 0600 (ADR-001). This module never imports ``tinytuya`` and
never imports Qt; only the CLI and GUI adapters above it touch the network.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import unicodedata
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

from avell_storm_rgb.application.config_paths import app_config_dir
from avell_storm_rgb.domain.bulb_color import BulbStatus, status_from_dps

__all__ = [
    "BulbFailure",
    "BulbInventory",
    "BulbRecord",
    "BulbStatus",
    "ImportFileError",
    "ImportReport",
    "ImportResult",
    "InventoryFileError",
    "Skipped",
    "UnknownTarget",
    "AmbiguousTarget",
    "default_inventory_path",
    "match_target",
    "parse_tinytuya_devices",
    "status_from_dps",
]

INVENTORY_VERSION = 1
INVENTORY_FILENAME = "tuya_devices.json"
DEFAULT_PROTOCOL = "3.3"
BULB_CATEGORY = "dj"

ImportStatus = Literal["added", "updated", "unchanged"]


@dataclass(frozen=True)
class BulbRecord:
    """One imported bulb. ``key`` is secret and never rendered (BR-3)."""

    id: str
    name: str
    key: str
    mac: str
    protocol: str = DEFAULT_PROTOCOL
    last_ip: str | None = None

    def __repr__(self) -> str:
        key_state = "'set'" if self.key else "'missing'"
        return (
            f"BulbRecord(id={self.id!r}, name={self.name!r}, key={key_state}, "
            f"mac={self.mac!r}, protocol={self.protocol!r}, last_ip={self.last_ip!r})"
        )


@dataclass(frozen=True)
class BulbFailure:
    """A failed bulb operation, safe to show and log (BR-3)."""

    reason: str  # short user text, e.g. "not reachable"
    detail: str  # "<ExceptionType>: <message>"; never a key or payload


@dataclass(frozen=True)
class Skipped:
    """A ``devices.json`` entry that was not imported, with the reason."""

    id: str
    name: str
    reason: str


@dataclass(frozen=True)
class ImportResult:
    """What ``upsert`` did with one imported record."""

    id: str
    name: str
    status: ImportStatus
    reason: str | None = None


@dataclass(frozen=True)
class ImportReport:
    """Outcome of an import; ``imported`` counts records that reached the file."""

    results: tuple[ImportResult, ...] = ()

    @property
    def imported(self) -> int:
        return len(self.results)


class InventoryFileError(Exception):
    """The inventory file exists but cannot be used (parse error, bad schema)."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{reason}: {path}")
        self.path = path
        self.reason = reason


class ImportFileError(Exception):
    """The tinytuya ``devices.json`` is not a JSON list of devices."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class UnknownTarget(Exception):
    """No bulb matched a CLI/GUI target."""

    def __init__(self, target: str, known: Sequence[str]) -> None:
        self.target = target
        self.known = tuple(known)
        names = ", ".join(self.known) if self.known else "none"
        super().__init__(f"no bulb named {target!r}. Known: {names}")


class AmbiguousTarget(Exception):
    """A name matched more than one bulb; the caller must use an id."""

    def __init__(self, target: str, ids: Sequence[str]) -> None:
        self.target = target
        self.ids = tuple(ids)
        super().__init__(
            f"{target!r} matches {len(self.ids)} bulbs; use the id: {', '.join(self.ids)}"
        )


def default_inventory_path() -> Path:
    """``tuya_devices.json`` in :func:`app_config_dir`."""
    return app_config_dir() / INVENTORY_FILENAME


def _fold(text: str) -> str:
    """Case- and accent-insensitive form used for name matching (BR-1)."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{where} must be a non-empty string, got {value!r}")
    return value


def _optional_text(value: Any, where: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{where} must be a string or null, got {value!r}")
    return value or None


def parse_tinytuya_devices(doc: Any) -> tuple[list[BulbRecord], list[Skipped]]:
    """Parse the wizard's ``devices.json`` (a decoded list, or its JSON text).

    Only ``dj`` entries with an id, a local key and a category become records.
    Everything else is returned as :class:`Skipped` with a fixed reason.
    """
    if isinstance(doc, str):
        try:
            doc = json.loads(doc)
        except json.JSONDecodeError as e:
            raise ImportFileError(f"invalid JSON at line {e.lineno} column {e.colno}") from e
    if not isinstance(doc, list):
        raise ImportFileError("expected a list of devices")

    records: list[BulbRecord] = []
    skipped: list[Skipped] = []
    for entry in doc:
        if not isinstance(entry, dict):
            skipped.append(Skipped("", "", "not an object"))
            continue
        name = entry.get("name") if isinstance(entry.get("name"), str) else ""
        bulb_id = entry.get("id") if isinstance(entry.get("id"), str) else ""
        if not bulb_id:
            skipped.append(Skipped("", name, "missing id"))
            continue
        key = entry.get("key")
        if not isinstance(key, str) or not key:
            skipped.append(Skipped(bulb_id, name, "no local key"))
            continue
        category = entry.get("category")
        if not isinstance(category, str) or not category:
            skipped.append(Skipped(bulb_id, name, "missing category"))
            continue
        if category != BULB_CATEGORY:
            skipped.append(Skipped(bulb_id, name, f"not a bulb (category {category})"))
            continue
        mac = entry.get("mac")
        version = entry.get("version")
        ip = entry.get("ip")
        records.append(
            BulbRecord(
                id=bulb_id,
                name=name,
                key=key,
                mac=mac.lower() if isinstance(mac, str) else "",
                protocol=version if isinstance(version, str) and version else DEFAULT_PROTOCOL,
                last_ip=ip if isinstance(ip, str) and ip else None,
            )
        )
    return records, skipped


def match_target(records: Sequence[BulbRecord], target: str) -> list[BulbRecord]:
    """Resolve ``"all"``, an exact device id, or a case/accent-insensitive name."""
    if target == "all":
        return list(records)
    for record in records:
        if record.id == target:
            return [record]
    folded = _fold(target)
    matches = [record for record in records if _fold(record.name) == folded]
    if not matches:
        raise UnknownTarget(target, [record.name for record in records])
    if len(matches) > 1:
        raise AmbiguousTarget(target, [record.id for record in matches])
    return matches


class BulbInventory:
    """Read and write the private bulb inventory file."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else default_inventory_path()

    @property
    def path(self) -> Path:
        return self._path

    def exists(self) -> bool:
        return self._path.is_file()

    def load(self) -> list[BulbRecord]:
        """Missing file → ``[]``. Unusable file → :class:`InventoryFileError`."""
        try:
            raw = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        except OSError as e:
            raise InventoryFileError(self._path, f"cannot read file ({e.strerror})") from e
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError as e:
            raise InventoryFileError(
                self._path, f"invalid JSON at line {e.lineno} column {e.colno}"
            ) from e
        return self._records_from(doc)

    def save(self, records: Sequence[BulbRecord]) -> None:
        """Atomic 0600 write: temp file in the same directory, then ``os.replace``."""
        with self._locked():
            self._write(records)

    def upsert(self, records: Sequence[BulbRecord]) -> ImportReport:
        """Insert new ids and update existing ones in place; never remove (BR-2)."""
        if not records:
            return ImportReport()
        with self._locked():
            merged = self.load()
            index = {record.id: i for i, record in enumerate(merged)}
            results: list[ImportResult] = []
            for incoming in records:
                position = index.get(incoming.id)
                if position is None:
                    index[incoming.id] = len(merged)
                    merged.append(incoming)
                    results.append(ImportResult(incoming.id, incoming.name, "added"))
                    continue
                current = merged[position]
                reasons = [
                    label
                    for label, old, new in (
                        ("key changed", current.key, incoming.key),
                        ("name changed", current.name, incoming.name),
                        ("mac changed", current.mac, incoming.mac),
                        ("protocol changed", current.protocol, incoming.protocol),
                    )
                    if old != new
                ]
                merged[position] = replace(
                    current,
                    name=incoming.name,
                    key=incoming.key,
                    mac=incoming.mac,
                    protocol=incoming.protocol,
                    last_ip=current.last_ip if current.last_ip is not None else incoming.last_ip,
                )
                results.append(
                    ImportResult(
                        incoming.id,
                        incoming.name,
                        "updated" if reasons else "unchanged",
                        ", ".join(reasons) if reasons else None,
                    )
                )
            self._write(merged)
        return ImportReport(tuple(results))

    def remove(self, bulb_id: str) -> BulbRecord | None:
        """Delete one record and its key; ``None`` when the id is not stored."""
        with self._locked():
            records = self.load()
            for i, record in enumerate(records):
                if record.id == bulb_id:
                    del records[i]
                    self._write(records)
                    return record
        return None

    def set_last_ip(self, bulb_id: str, ip: str) -> None:
        """Remember the IP that last answered for ``bulb_id`` (no-op when unchanged)."""
        with self._locked():
            records = self.load()
            for i, record in enumerate(records):
                if record.id == bulb_id:
                    if record.last_ip != ip:
                        records[i] = replace(record, last_ip=ip)
                        self._write(records)
                    return

    def _records_from(self, doc: Any) -> list[BulbRecord]:
        if not isinstance(doc, dict):
            raise InventoryFileError(
                self._path, f"expected an object, got {type(doc).__name__}"
            )
        version = doc.get("version")
        if version != INVENTORY_VERSION:
            raise InventoryFileError(self._path, f"unsupported version {version!r}")
        devices = doc.get("devices")
        if not isinstance(devices, list):
            raise InventoryFileError(self._path, "devices must be a list")
        records: list[BulbRecord] = []
        for i, entry in enumerate(devices):
            where = f"devices[{i}]"
            if not isinstance(entry, dict):
                raise InventoryFileError(self._path, f"{where} must be an object")
            try:
                records.append(
                    BulbRecord(
                        id=_text(entry.get("id"), f"{where}.id"),
                        name=_text(entry.get("name"), f"{where}.name"),
                        key=_text(entry.get("key"), f"{where}.key"),
                        mac=_text(entry.get("mac"), f"{where}.mac"),
                        protocol=_optional_text(entry.get("protocol"), f"{where}.protocol")
                        or DEFAULT_PROTOCOL,
                        last_ip=_optional_text(entry.get("last_ip"), f"{where}.last_ip"),
                    )
                )
            except ValueError as e:
                raise InventoryFileError(self._path, str(e)) from e
        return records

    @staticmethod
    def _to_dict(records: Sequence[BulbRecord]) -> dict[str, Any]:
        return {
            "version": INVENTORY_VERSION,
            "devices": [
                {
                    "id": record.id,
                    "name": record.name,
                    "key": record.key,
                    "mac": record.mac,
                    "protocol": record.protocol,
                    "last_ip": record.last_ip,
                }
                for record in records
            ],
        }

    def _write(self, records: Sequence[BulbRecord]) -> None:
        directory = self._path.parent
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        data = json.dumps(self._to_dict(records), indent=2) + "\n"
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tuya_devices.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.chmod(tmp, 0o600)
            os.replace(tmp, self._path)
        except BaseException:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise

    @contextmanager
    def _locked(self) -> Iterator[None]:
        """Serialise writers through an advisory lock next to the inventory (ADR-001)."""
        self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock_path = self._path.with_name(self._path.name + ".lock")
        fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)
