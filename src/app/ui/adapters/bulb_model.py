"""List model for imported bulbs; rows use the same keys as ``BulbsBackend.bulb(id)``."""

from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

#: Role names, in role order (``_spec.md`` → ``BulbListModel`` roles).
ROLE_KEYS = (
    "bulbId",
    "title",
    "subtitle",
    "remembered",
    "available",
    "lightOn",
    "stateKnown",
    "unavailableReason",
    "mode",
    "brightness",
    "temperature",
    "rgb",
    "follow",
    "ip",
    "busy",
)
_FIRST_ROLE = Qt.ItemDataRole.UserRole + 1


class BulbListModel(QAbstractListModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[dict] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def roleNames(self) -> dict[int, bytes]:
        return {_FIRST_ROLE + i: key.encode() for i, key in enumerate(ROLE_KEYS)}

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._rows):
            return None
        row = self._rows[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return row["title"]
        i = role - _FIRST_ROLE
        return row[ROLE_KEYS[i]] if 0 <= i < len(ROLE_KEYS) else None

    def rows(self) -> list[dict]:
        return [dict(r) for r in self._rows]

    def set_rows(self, rows: list[dict]) -> None:
        if [r["bulbId"] for r in rows] == [r["bulbId"] for r in self._rows]:
            self._rows = rows
            if rows:
                self.dataChanged.emit(self.index(0), self.index(len(rows) - 1))
            return
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
