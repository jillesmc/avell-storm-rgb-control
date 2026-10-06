import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    id: root
    spacing: Kirigami.Units.smallSpacing

    required property var keyboard
    property int repaintTick: 0
    property bool gridInteractive: keyboard ? keyboard.connected : false

    signal cellClicked(int visualRow, int col, bool hasOverride)

    function _deviceRowLabel(visualRow) {
        if (!keyboard)
            return ""
        return String(keyboard.deviceRowForVisualRow(visualRow))
    }

    Connections {
        target: root.keyboard
        function onCalibrationChanged() { root.repaintTick++ }
        function onCalibrationPendingChanged() { root.repaintTick++ }
        function onCalibrationModeChanged() { root.repaintTick++ }
    }

    Label {
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
        text: qsTr("Top row = top of keyboard (device row 5). Numbers match firmware / profile JSON.")
        font.italic: true
        opacity: 0.85
    }

    readonly property int _cols: keyboard ? keyboard.gridCols : 21
    readonly property int _rows: keyboard ? keyboard.gridRows : 6
    readonly property real _horizontalPadding: 32
    readonly property bool _visualV2: keyboard && keyboard.layoutVisualVersion === 2
    readonly property real _boundsWidthU: _visualV2 ? keyboard.layoutBoundsWidthU : 21
    readonly property real _unitPx: Math.max(
        8,
        Math.floor((Math.max(width, 1) - _horizontalPadding) / Math.max(_boundsWidthU, 1)))
    readonly property real _contentWidth: _unitPx * _boundsWidthU + _horizontalPadding
    readonly property real _cellGap: Math.max(2, Math.floor(_unitPx * 0.15))
    readonly property real _cellSize: Math.max(
        8,
        Math.floor((_contentWidth - _cellGap * _cols) / (_cols + 1)))
    readonly property real _labelFontPx: Math.max(5, Math.floor(_cellSize * 0.38))
    readonly property real _headerFontPx: Math.max(6, Math.floor(_cellSize * 0.42))
    readonly property color _pendingFill: Qt.alpha("#ff9800", 0.62)
    readonly property color _pendingBorder: "#ff9800"
    readonly property color _selectedFill: Qt.alpha(Kirigami.Theme.highlightColor, 0.35)

    Item {
        id: gridHost
        Layout.fillWidth: true
        Layout.preferredWidth: root._contentWidth
        Layout.alignment: Qt.AlignHCenter
        implicitHeight: (root._rows + 1) * (root._cellSize + root._cellGap) + root._cellGap

        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            width: root._contentWidth
            spacing: root._cellGap

            Row {
                spacing: root._cellGap
                Item {
                    width: root._cellSize
                    height: root._cellSize
                }
                Repeater {
                    model: root._cols
                    delegate: Label {
                        required property int index
                        width: root._cellSize
                        height: root._cellSize
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        text: String(index)
                        font.pixelSize: root._headerFontPx
                        opacity: 0.75
                    }
                }
            }

            Repeater {
                model: root._rows
                delegate: Row {
                    required property int index
                    readonly property int visualRow: index
                    spacing: root._cellGap

                    Label {
                        width: root._cellSize
                        height: root._cellSize
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        text: root._deviceRowLabel(visualRow)
                        font.bold: true
                        font.pixelSize: root._headerFontPx
                    }

                    Repeater {
                        model: root._cols
                        delegate: Rectangle {
                            required property int index
                            readonly property int col: index
                            readonly property int tick: root.repaintTick
                            readonly property bool pending: {
                                void tick
                                return root.keyboard
                                    && root.keyboard.isCalibrationCellPending(visualRow, col)
                            }
                            readonly property string assignee: {
                                void tick
                                return root.keyboard
                                    ? root.keyboard.calibrationCellAssignee(visualRow, col)
                                    : ""
                            }
                            readonly property string profileHint: {
                                void tick
                                return root.keyboard
                                    ? root.keyboard.calibrationCellProfileHint(visualRow, col)
                                    : ""
                            }
                            readonly property bool matched: assignee.length > 0
                            readonly property bool unused: {
                                void tick
                                return root.keyboard
                                    && root.keyboard.isCalibrationCellUnused(visualRow, col)
                            }
                            readonly property bool selected: {
                                void tick
                                return root.keyboard
                                    && root.keyboard.isCalibrationCellSelected(visualRow, col)
                            }
                            readonly property bool conflict: {
                                void tick
                                return root.keyboard
                                    && root.keyboard.isCalibrationCellConflict(visualRow, col)
                            }

                            width: root._cellSize
                            height: root._cellSize
                            radius: 3
                            clip: true
                            border.width: pending ? 3 : (selected ? 2 : 1)
                            border.color: conflict
                                ? "#d32f2f"
                                : (pending
                                   ? root._pendingBorder
                                   : (selected
                                      ? Kirigami.Theme.highlightColor
                                      : Qt.rgba(Kirigami.Theme.textColor.r,
                                                Kirigami.Theme.textColor.g,
                                                Kirigami.Theme.textColor.b, 0.25)))
                            color: {
                                if (conflict)
                                    return Qt.alpha("#d32f2f", 0.15)
                                if (pending)
                                    return root._pendingFill
                                if (selected)
                                    return root._selectedFill
                                if (matched)
                                    return Qt.alpha(Kirigami.Theme.positiveTextColor, 0.2)
                                if (unused)
                                    return Qt.alpha(Kirigami.Theme.disabledTextColor, 0.12)
                                return Kirigami.Theme.alternateBackgroundColor
                            }
                            opacity: root.gridInteractive ? 1.0 : 0.45

                            Rectangle {
                                anchors.fill: parent
                                radius: parent.radius
                                visible: pending && !conflict
                                color: "transparent"
                                border.width: 1
                                border.color: Qt.alpha("#ffffff", 0.35)
                            }

                            Label {
                                anchors.bottom: parent.bottom
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.bottomMargin: 1
                                visible: pending && !matched && !conflict
                                text: "●"
                                font.pixelSize: Math.max(4, root._labelFontPx - 1)
                                color: root._pendingBorder
                            }

                            Label {
                                anchors.centerIn: parent
                                width: Math.max(1, parent.width - 4)
                                horizontalAlignment: Text.AlignHCenter
                                elide: Text.ElideRight
                                visible: matched
                                text: assignee.length > 6 ? assignee.substring(0, 5) + "…" : assignee
                                font.pixelSize: root._labelFontPx
                                color: Kirigami.Theme.textColor
                            }

                            Label {
                                anchors.centerIn: parent
                                visible: !matched && unused
                                text: "—"
                                font.pixelSize: root._labelFontPx
                                color: Kirigami.Theme.disabledTextColor
                            }

                            Label {
                                anchors.centerIn: parent
                                width: Math.max(1, parent.width - 4)
                                horizontalAlignment: Text.AlignHCenter
                                elide: Text.ElideRight
                                visible: !matched && !unused && profileHint.length > 0
                                text: profileHint.length > 6
                                      ? profileHint.substring(0, 5) + "…"
                                      : profileHint
                                font.pixelSize: root._labelFontPx
                                font.italic: true
                                opacity: 0.55
                                color: Kirigami.Theme.textColor
                            }

                            Label {
                                anchors.top: parent.top
                                anchors.right: parent.right
                                anchors.margins: 1
                                visible: matched && !conflict
                                text: "✓"
                                font.pixelSize: root._labelFontPx
                                color: Kirigami.Theme.positiveTextColor
                            }

                            MouseArea {
                                anchors.fill: parent
                                enabled: root.gridInteractive
                                hoverEnabled: true
                                ToolTip.visible: containsMouse
                                ToolTip.text: {
                                    var dr = root.keyboard
                                        ? root.keyboard.deviceRowForVisualRow(visualRow)
                                        : -1
                                    var base = qsTr("Device row %1, col %2").arg(dr).arg(col)
                                    if (assignee.length > 0)
                                        return base + "\n" + qsTr("Matched: %1 — click to select for clearing").arg(assignee)
                                    if (unused)
                                        return base + "\n" + qsTr("Marked unused — click to calibrate")
                                    if (profileHint.length > 0)
                                        return base + "\n" + qsTr("Profile default: %1").arg(profileHint)
                                    if (pending)
                                        return base + "\n" + qsTr("Selected — press the physical key")
                                    return base + "\n" + qsTr("Click to light this LED")
                                }
                                onClicked: root.cellClicked(visualRow, col, matched)
                            }
                        }
                    }
                }
            }
        }
    }
}
