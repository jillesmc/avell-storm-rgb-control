import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    id: root
    spacing: 8

    /** Cell edge length in pixels (larger = easier to tap). */
    property int cellSize: 18

    required property var keyboard
    signal cellClicked(int row, int col)

    GridLayout {
        id: gridLayout
        columns: keyboard ? keyboard.gridCols : 1
        rowSpacing: 3
        columnSpacing: 3

        Repeater {
            model: keyboard ? (keyboard.gridRows * keyboard.gridCols) : 0
            delegate: Rectangle {
                required property int index
                readonly property int row: Math.floor(index / root.keyboard.gridCols)
                readonly property int col: index % root.keyboard.gridCols

                width: root.cellSize
                height: root.cellSize
                border.width: 1
                border.color: Kirigami.Theme.textColor
                color: {
                    var _ = root.keyboard.keyGridEpoch
                    return root.keyboard.keyCellHex(row, col)
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    ToolTip.visible: containsMouse
                    ToolTip.text: qsTr("Row %1, col %2 — click to pick color").arg(row).arg(col)
                    onClicked: root.cellClicked(row, col)
                }
            }
        }
    }
}
