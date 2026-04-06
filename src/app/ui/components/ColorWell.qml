import QtQuick
import QtQuick.Controls
import org.kde.kirigami as Kirigami

Rectangle {
    id: root

    width: 28
    height: 28
    radius: 4
    border.width: 1
    border.color: Kirigami.Theme.textColor
    color: fillColor

    property color fillColor: "#808080"
    property string toolTipText: ""

    signal clicked()

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        ToolTip.visible: containsMouse && root.toolTipText.length > 0
        ToolTip.text: root.toolTipText
        onClicked: root.clicked()
    }
}
