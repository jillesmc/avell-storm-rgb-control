import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.Chip {
    id: root

    property string effectName: ""
    property bool selected: false

    closable: false
    display: QQC2.AbstractButton.TextOnly
    text: effectName
    checked: selected

    implicitHeight: Math.max(implicitContentHeight, Kirigami.Units.gridUnit * 2.5)
    padding: Kirigami.Units.smallSpacing
    leftPadding: Kirigami.Units.largeSpacing
    rightPadding: Kirigami.Units.largeSpacing

    QQC2.ToolTip.visible: hovered && effectName.length > 0
    QQC2.ToolTip.text: effectName
    hoverEnabled: true

    onClicked: root.activated()

    Component.onCompleted: {
        labelItem.elide = Text.ElideRight
        labelItem.maximumLineCount = 1
        labelItem.wrapMode = Text.NoWrap
    }

    signal activated()
}
