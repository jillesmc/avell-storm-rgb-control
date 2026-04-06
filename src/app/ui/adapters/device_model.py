from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from app.core.devices import enumerate_usb_devices


class DeviceListModel(QAbstractListModel):
    KindRole = Qt.ItemDataRole.UserRole + 1
    BusRole = Qt.ItemDataRole.UserRole + 2
    AddrRole = Qt.ItemDataRole.UserRole + 3
    LabelRole = Qt.ItemDataRole.UserRole + 4

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[dict] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.KindRole: b"kind",
            self.BusRole: b"bus",
            self.AddrRole: b"addr",
            self.LabelRole: b"label",
        }

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        row = self._items[index.row()]
        if role == self.KindRole:
            return row["kind"]
        if role == self.BusRole:
            return row["bus"]
        if role == self.AddrRole:
            return row["addr"]
        if role == self.LabelRole:
            return row["label"]
        if role == Qt.ItemDataRole.DisplayRole:
            return row["label"]
        return None

    def refresh(self) -> None:
        self.beginResetModel()
        self._items = enumerate_usb_devices()
        self.endResetModel()
