pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    id: root

    required property var keyboard
    property var selectedKeyIds: []
    property var calibratedKeyIds: []
    property var conflictKeyIds: []
    property bool showCalibratedBadge: false
    property bool readOnly: false
    /** When true, keys can be clicked even if ``readOnly`` is set (calibration layout pick). */
    property bool layoutInteractive: false
    signal keyActivated(string keyId)
    signal selectionChanged(var keyIds)

    readonly property bool visualV2: keyboard && keyboard.layoutVisualVersion === 2
    readonly property real keyGapU: visualV2 ? keyboard.layoutKeyGapU : 0
    readonly property real boundsMinX: visualV2 ? keyboard.layoutBoundsMinX : 0
    readonly property real boundsMinY: visualV2 ? keyboard.layoutBoundsMinY : 0
    readonly property real boundsWidthU: visualV2 ? keyboard.layoutBoundsWidthU : 21
    readonly property real boundsHeightU: visualV2 ? keyboard.layoutBoundsHeightU : 6

    readonly property real rowGap: Kirigami.Units.smallSpacing
    readonly property real colGap: 2
    readonly property real unitPx: visualV2
        ? Math.max(12, Math.floor((Math.max(width, 1) - 32) / Math.max(boundsWidthU, 1)))
        : Math.max(12, Math.floor((Math.max(width, 1) - colGap * 20) / 21))
    readonly property real contentWidth: visualV2
        ? unitPx * boundsWidthU + 32
        : unitPx * 21 + colGap * 20
    readonly property real contentHeight: visualV2
        ? unitPx * boundsHeightU + rowGap * Math.max(0, Math.ceil(boundsHeightU) - 1) + Kirigami.Units.smallSpacing
        : unitPx * 6 + rowGap * 5

    readonly property real keyLabelFontPx: Math.max(6, Math.floor(unitPx * 0.42))
    readonly property real keySecondaryFontPx: Math.max(5, Math.floor(unitPx * 0.3))
    readonly property real keyBadgeFontPx: Math.max(6, Math.floor(unitPx * 0.32))

    implicitHeight: contentHeight + Kirigami.Units.largeSpacing

    function _normalizeSelection(ids) {
        var out = []
        var seen = {}
        for (var i = 0; i < ids.length; ++i) {
            var id = String(ids[i])
            if (!id.length || id === "_spacer" || seen[id])
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

    function _partRect(part) {
        if (root.visualV2) {
            var xU = part.xU !== undefined ? part.xU : (part.x !== undefined ? part.x : 0)
            var yU = part.yU !== undefined ? part.yU : (part.y !== undefined ? part.y : 0)
            var wU = part.wU !== undefined ? part.wU : (part.w !== undefined ? part.w : 1)
            var hU = part.hU !== undefined ? part.hU : (part.h !== undefined ? part.h : 1)
            return Qt.rect(
                (xU - root.boundsMinX) * root.unitPx,
                yU * root.unitPx + yU * root.rowGap,
                wU * root.unitPx,
                hU * root.unitPx + (hU - 1) * root.rowGap
            )
        }
        return Qt.rect(
            part.x * unitPx + part.x * colGap,
            part.y * unitPx + part.y * rowGap,
            part.w * unitPx + (part.w - 1) * colGap,
            part.h * unitPx + (part.h - 1) * rowGap
        )
    }

    function _keyParts(key) {
        if (key.visualParts !== undefined && key.visualParts.length > 0)
            return key.visualParts
        if (key.isSpacer)
            return [{"x": key.x, "y": key.y, "w": key.w, "h": key.h, "spacer": true}]
        if (root.visualV2) {
            return [{
                "xU": key.xU,
                "yU": key.yU,
                "wU": key.wU,
                "hU": key.hU
            }]
        }
        return [{"x": key.x, "y": key.y, "w": key.w, "h": key.h}]
    }

    function _isoEnterBounds(parts) {
        if (!parts || parts.length < 2)
            return Qt.rect(0, 0, 0, 0)
        var top = root._partRect(parts[0])
        var bot = root._partRect(parts[1])
        var left = Math.min(top.x, bot.x)
        return Qt.rect(
            left,
            top.y,
            Math.max(top.x + top.width, bot.x + bot.width) - left,
            bot.y + bot.height - top.y
        )
    }

    function _paintIsoEnter(ctx, parts, bounds, fillColor, strokeColor, lineWidth) {
        var top = root._partRect(parts[0])
        var bot = root._partRect(parts[1])
        var ox = bounds.x
        var oy = bounds.y
        var tx = top.x - ox
        var ty = top.y - oy
        var tw = top.width
        var th = top.height
        var bx = bot.x - ox
        var by = bot.y - oy
        var bw = bot.width
        var bh = bot.height
        var junctionY = ty + th

        ctx.beginPath()
        ctx.moveTo(tx, ty)
        ctx.lineTo(tx + tw, ty)
        ctx.lineTo(tx + tw, junctionY)
        ctx.lineTo(bx + bw, junctionY)
        ctx.lineTo(bx + bw, by + bh)
        ctx.lineTo(bx, by + bh)
        ctx.lineTo(bx, junctionY)
        ctx.lineTo(tx, junctionY)
        ctx.closePath()
        ctx.fillStyle = fillColor
        ctx.fill()
        if (lineWidth > 0) {
            ctx.strokeStyle = strokeColor
            ctx.lineWidth = lineWidth
            ctx.stroke()
        }
    }

    function _rectIntersects(a, b) {
        return !(a.x + a.width < b.x || b.x + b.width < a.x || a.y + a.height < b.y || b.y + b.height < a.y)
    }

    function _keyHitRect(key) {
        if (key.visualShape === "isoEnter") {
            return _isoEnterBounds(_keyParts(key))
        }
        var parts = _keyParts(key)
        if (!parts.length)
            return Qt.rect(0, 0, 0, 0)
        var hit = _partRect(parts[0])
        for (var p = 1; p < parts.length; ++p) {
            var part = _partRect(parts[p])
            var right = Math.max(hit.x + hit.width, part.x + part.width)
            var bottom = Math.max(hit.y + hit.height, part.y + part.height)
            hit = Qt.rect(
                Math.min(hit.x, part.x),
                Math.min(hit.y, part.y),
                right - Math.min(hit.x, part.x),
                bottom - Math.min(hit.y, part.y)
            )
        }
        return hit
    }

    function _pointInRect(px, py, rect) {
        return px >= rect.x && px <= rect.x + rect.width
            && py >= rect.y && py <= rect.y + rect.height
    }

    function _keyAt(px, py) {
        var keys = keyboard ? keyboard.keyLayoutKeys : []
        for (var i = 0; i < keys.length; ++i) {
            var key = keys[i]
            if (key.isSpacer)
                continue
            if (_pointInRect(px, py, _keyHitRect(key)))
                return String(key.keyId)
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
            if (key.isSpacer)
                continue
            if (_rectIntersects(_keyHitRect(key), area))
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
            delegate: Item {
                id: keyRoot
                anchors.fill: parent
                required property var modelData
                readonly property string keyId: String(modelData.keyId)
                readonly property bool isSpacer: modelData.isSpacer === true || keyId === "_spacer"
                readonly property bool selected: !isSpacer && root.selectedKeyIds.indexOf(keyId) >= 0
                readonly property bool calibrated: root.calibratedKeyIds.indexOf(keyId) >= 0
                readonly property bool conflict: root.conflictKeyIds.indexOf(keyId) >= 0
                readonly property int epoch: root.keyboard ? root.keyboard.keyGridEpoch : 0
                readonly property color keyColor: {
                    var tick = epoch
                    void tick
                    if (isSpacer)
                        return "transparent"
                    return root.keyboard ? root.keyboard.keyHexById(keyId) : "#353535"
                }
                readonly property var parts: root._keyParts(modelData)
                readonly property bool isoEnter: modelData.visualShape === "isoEnter"
                readonly property rect isoBounds: root._isoEnterBounds(keyRoot.parts)

                Canvas {
                    id: isoEnterCanvas
                    visible: keyRoot.isoEnter && !keyRoot.isSpacer
                    clip: true
                    x: keyRoot.isoBounds.x
                    y: keyRoot.isoBounds.y
                    width: keyRoot.isoBounds.width
                    height: keyRoot.isoBounds.height
                    readonly property bool isDarkAppliedColor: (keyRoot.keyColor.r * 0.299
                        + keyRoot.keyColor.g * 0.587 + keyRoot.keyColor.b * 0.114) < 0.45
                    readonly property color keyLabelColor: isDarkAppliedColor
                        ? Qt.rgba(1, 1, 1, 0.95) : Qt.rgba(0, 0, 0, 0.9)
                    readonly property real strokeWidth: keyRoot.selected ? 2 : 1
                    readonly property color strokeColor: keyRoot.conflict
                        ? "#d32f2f"
                        : (keyRoot.selected
                           ? Kirigami.Theme.highlightColor
                           : (keyRoot.calibrated ? "#ff9800"
                              : Qt.alpha(Kirigami.Theme.textColor, 0.4)))

                    readonly property int repaintEpoch: keyRoot.epoch
                    onRepaintEpochChanged: requestPaint()
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    Component.onCompleted: requestPaint()

                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.clearRect(0, 0, width, height)
                        root._paintIsoEnter(
                            ctx,
                            keyRoot.parts,
                            keyRoot.isoBounds,
                            keyRoot.keyColor,
                            strokeColor,
                            strokeWidth
                        )
                    }

                    Label {
                        anchors.centerIn: parent
                        width: Math.max(1, parent.width - 6)
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                        text: keyRoot.modelData.label
                        font.pixelSize: root.keyLabelFontPx
                        color: isoEnterCanvas.keyLabelColor
                    }
                    Label {
                        visible: String(keyRoot.modelData.secondaryLabel).length > 0
                        anchors.top: parent.top
                        anchors.right: parent.right
                        anchors.topMargin: 1
                        anchors.rightMargin: 2
                        width: Math.max(1, parent.width * 0.55)
                        horizontalAlignment: Text.AlignRight
                        elide: Text.ElideRight
                        text: keyRoot.modelData.secondaryLabel
                        font.pixelSize: root.keySecondaryFontPx
                        color: isoEnterCanvas.keyLabelColor
                        opacity: 0.8
                    }
                    Label {
                        visible: root.showCalibratedBadge && keyRoot.calibrated
                        anchors.bottom: parent.bottom
                        anchors.right: parent.right
                        anchors.margins: 2
                        text: "✓"
                        font.pixelSize: root.keyBadgeFontPx
                        font.bold: true
                        color: Kirigami.Theme.positiveTextColor
                    }

                    MouseArea {
                        anchors.fill: parent
                        visible: keyRoot.conflict && root.keyboard
                        hoverEnabled: true
                        acceptedButtons: Qt.NoButton
                        ToolTip.visible: containsMouse
                        ToolTip.text: root.keyboard.calibrationConflictTooltip(keyRoot.keyId)
                    }
                }

                Repeater {
                    // Delegates parent to keyRoot, not this Repeater — empty model hides parts.
                    model: keyRoot.isoEnter ? [] : keyRoot.parts
                    delegate: Rectangle {
                        required property int index
                        required property var modelData
                        readonly property bool partSpacer: keyRoot.isSpacer || modelData.spacer === true
                        readonly property bool isDarkAppliedColor: !partSpacer
                            && (keyRoot.keyColor.r * 0.299 + keyRoot.keyColor.g * 0.587 + keyRoot.keyColor.b * 0.114) < 0.45
                        readonly property color keyLabelColor: isDarkAppliedColor ? Qt.rgba(1, 1, 1, 0.95) : Qt.rgba(0, 0, 0, 0.9)
                        readonly property rect partRect: root._partRect(modelData)

                        x: partRect.x
                        y: partRect.y
                        width: partRect.width
                        height: partRect.height
                        radius: partSpacer ? 0 : 4
                        clip: !partSpacer
                        border.width: partSpacer ? 0 : (keyRoot.selected ? 2 : 1)
                        border.color: partSpacer ? "transparent" : (keyRoot.selected
                                      ? Kirigami.Theme.highlightColor
                                      : (keyRoot.conflict
                                         ? "#d32f2f"
                                         : (keyRoot.calibrated ? "#ff9800" : Qt.alpha(Kirigami.Theme.textColor, 0.4))))
                        color: partSpacer ? "transparent" : keyRoot.keyColor

                        Label {
                            visible: index === 0 && !partSpacer
                            anchors.centerIn: parent
                            width: Math.max(1, parent.width - 6)
                            horizontalAlignment: Text.AlignHCenter
                            elide: Text.ElideRight
                            text: keyRoot.modelData.label
                            font.pixelSize: root.keyLabelFontPx
                            color: keyLabelColor
                        }
                        Label {
                            visible: index === 0 && !partSpacer
                                    && String(keyRoot.modelData.secondaryLabel).length > 0
                            anchors.top: parent.top
                            anchors.right: parent.right
                            anchors.topMargin: 1
                            anchors.rightMargin: 2
                            width: Math.max(1, parent.width * 0.55)
                            horizontalAlignment: Text.AlignRight
                            elide: Text.ElideRight
                            text: keyRoot.modelData.secondaryLabel
                            font.pixelSize: root.keySecondaryFontPx
                            color: keyLabelColor
                            opacity: 0.8
                        }
                        Label {
                            visible: index === 0 && !partSpacer
                                    && root.showCalibratedBadge && keyRoot.calibrated
                            anchors.bottom: parent.bottom
                            anchors.right: parent.right
                            anchors.margins: 2
                            text: "✓"
                            font.pixelSize: root.keyBadgeFontPx
                            font.bold: true
                            color: Kirigami.Theme.positiveTextColor
                        }

                        MouseArea {
                            anchors.fill: parent
                            visible: keyRoot.conflict && root.keyboard
                            hoverEnabled: true
                            acceptedButtons: Qt.NoButton
                            ToolTip.visible: containsMouse
                            ToolTip.text: root.keyboard.calibrationConflictTooltip(keyRoot.keyId)
                        }
                    }
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
            enabled: !root.readOnly || root.layoutInteractive
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
                    var kid = root._keyAt(root.dragNowX, root.dragNowY)
                    if (kid.length)
                        root.keyActivated(kid)
                } else {
                    root._updateSelectionFromDrag()
                }
                root.dragging = false
            }
        }
    }
}
