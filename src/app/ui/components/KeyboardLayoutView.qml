pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    id: root

    required property var keyboard
    property var selectedKeyIds: []
    signal keyActivated(string keyId)
    signal selectionChanged(var keyIds)

    // Fit exactly into available width to avoid clipping on the right edge.
    property real unitSize: Math.max(12, Math.floor((Math.max(width, 1) - colGap * 20) / 21))
    readonly property real rowGap: Kirigami.Units.smallSpacing
    readonly property real colGap: 2
    readonly property real contentWidth: unitSize * 21 + colGap * 20
    readonly property real contentHeight: unitSize * 6 + rowGap * 5

    implicitHeight: contentHeight + Kirigami.Units.largeSpacing

    function _normalizeSelection(ids) {
        var out = []
        var seen = {}
        for (var i = 0; i < ids.length; ++i) {
            var id = String(ids[i])
            if (!id.length || seen[id])
                continue
            seen[id] = true
            out.push(id)
        }
        out.sort()
        return out
    }

    function _sameSelection(a, b) {
        if (a.length !== b.length)
            return false
        for (var i = 0; i < a.length; ++i) {
            if (String(a[i]) !== String(b[i]))
                return false
        }
        return true
    }

    function _keyRect(key) {
        return Qt.rect(
            key.x * unitSize + key.x * colGap,
            key.y * unitSize + key.y * rowGap,
            key.w * unitSize + (key.w - 1) * colGap,
            key.h * unitSize + (key.h - 1) * rowGap
        )
    }

    function _rectIntersects(a, b) {
        return !(a.x + a.width < b.x || b.x + b.width < a.x || a.y + a.height < b.y || b.y + b.height < a.y)
    }

    function _keyAt(px, py) {
        var keys = keyboard ? keyboard.keyLayoutKeys : []
        for (var i = 0; i < keys.length; ++i) {
            var kr = _keyRect(keys[i])
            if (px >= kr.x && px <= kr.x + kr.width && py >= kr.y && py <= kr.y + kr.height)
                return String(keys[i].keyId)
        }
        return ""
    }

    function _updateSelectionFromDrag() {
        var keys = keyboard ? keyboard.keyLayoutKeys : []
        var picked = []
        var area = Qt.rect(
            Math.min(dragStartX, dragNowX),
            Math.min(dragStartY, dragNowY),
            Math.abs(dragNowX - dragStartX),
            Math.abs(dragNowY - dragStartY)
        )
        for (var i = 0; i < keys.length; ++i) {
            var key = keys[i]
            if (_rectIntersects(_keyRect(key), area))
                picked.push(String(key.keyId))
        }
        var normalized = _normalizeSelection(picked)
        if (!_sameSelection(selectedKeyIds, normalized)) {
            selectedKeyIds = normalized
            selectionChanged(normalized)
        }
    }

    property real dragStartX: 0
    property real dragStartY: 0
    property real dragNowX: 0
    property real dragNowY: 0
    property bool dragging: false

    Item {
        id: board
        anchors.horizontalCenter: parent.horizontalCenter
        width: root.contentWidth
        height: root.contentHeight

        Repeater {
            model: root.keyboard ? root.keyboard.keyLayoutKeys : []
            delegate: Rectangle {
                id: keyDelegate
                required property var modelData
                readonly property bool selected: root.selectedKeyIds.indexOf(String(modelData.keyId)) >= 0
                readonly property int epoch: root.keyboard ? root.keyboard.keyGridEpoch : 0
                readonly property color keyColor: {
                    // Depend explicitly on keyGridEpoch so repaint happens after setKeyById/setKeysByIdColor.
                    var tick = epoch
                    void tick
                    return root.keyboard ? root.keyboard.keyHexById(String(modelData.keyId)) : "#353535"
                }
                readonly property bool isDarkAppliedColor: (keyColor.r * 0.299 + keyColor.g * 0.587 + keyColor.b * 0.114) < 0.45
                readonly property color keyLabelColor: isDarkAppliedColor ? Qt.rgba(1, 1, 1, 0.95) : Qt.rgba(0, 0, 0, 0.9)
                readonly property color keyOutlineColor: isDarkAppliedColor ? Qt.rgba(1, 1, 1, 0.7) : Qt.rgba(0, 0, 0, 0.7)

                x: modelData.x * root.unitSize + modelData.x * root.colGap
                y: modelData.y * root.unitSize + modelData.y * root.rowGap
                width: modelData.w * root.unitSize + (modelData.w - 1) * root.colGap
                height: modelData.h * root.unitSize + (modelData.h - 1) * root.rowGap
                radius: 4
                border.width: selected ? 2 : 1
                border.color: selected ? Kirigami.Theme.highlightColor : Qt.alpha(Kirigami.Theme.textColor, 0.4)
                color: keyColor

                Label {
                    anchors.centerIn: parent
                    text: keyDelegate.modelData.label
                    font.pixelSize: Math.max(9, Kirigami.Theme.smallFont.pixelSize)
                    style: Text.Normal
                    color: keyDelegate.keyLabelColor
                }

                ToolTip.visible: keyMouse.containsMouse
                ToolTip.text: qsTr("%1").arg(keyDelegate.modelData.label)
                MouseArea {
                    id: keyMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.NoButton
                }
            }
        }

        Rectangle {
            visible: root.dragging
            x: Math.min(root.dragStartX, root.dragNowX)
            y: Math.min(root.dragStartY, root.dragNowY)
            width: Math.abs(root.dragNowX - root.dragStartX)
            height: Math.abs(root.dragNowY - root.dragStartY)
            color: Qt.alpha(Kirigami.Theme.highlightColor, 0.2)
            border.width: 1
            border.color: Kirigami.Theme.highlightColor
        }

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            hoverEnabled: false
            propagateComposedEvents: true
            onPressed: function (mouse) {
                root.dragStartX = mouse.x
                root.dragStartY = mouse.y
                root.dragNowX = mouse.x
                root.dragNowY = mouse.y
                root.dragging = true
            }
            onPositionChanged: function (mouse) {
                if (!root.dragging)
                    return
                root.dragNowX = Math.max(0, Math.min(board.width, mouse.x))
                root.dragNowY = Math.max(0, Math.min(board.height, mouse.y))
                root._updateSelectionFromDrag()
            }
            onReleased: function (mouse) {
                if (!root.dragging)
                    return
                root.dragNowX = Math.max(0, Math.min(board.width, mouse.x))
                root.dragNowY = Math.max(0, Math.min(board.height, mouse.y))
                var dragDistance = Math.abs(root.dragNowX - root.dragStartX) + Math.abs(root.dragNowY - root.dragStartY)
                if (dragDistance < 6) {
                    var keyId = root._keyAt(root.dragNowX, root.dragNowY)
                    if (keyId.length)
                        root.keyActivated(keyId)
                } else {
                    root._updateSelectionFromDrag()
                }
                root.dragging = false
            }
        }
    }
}
