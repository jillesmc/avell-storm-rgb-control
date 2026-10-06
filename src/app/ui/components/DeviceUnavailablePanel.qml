import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

/**
 * Remembered device that is not connected: says why, offers Retry and Forget.
 * PlaceholderMessage holds one action (Retry); Forget is a flat button below it.
 */
Item {
    id: root

    property string deviceTitle: ""
    property string reason: ""

    signal retryRequested()
    signal forgetRequested()

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - Kirigami.Units.gridUnit * 4, Kirigami.Units.gridUnit * 30)
        spacing: Kirigami.Units.largeSpacing

        Kirigami.PlaceholderMessage {
            Layout.fillWidth: true
            icon.name: "network-disconnect-symbolic"
            text: qsTr("%1 unavailable").arg(root.deviceTitle)
            explanation: root.reason
            helpfulAction: Kirigami.Action {
                text: qsTr("Retry")
                icon.name: "view-refresh-symbolic"
                onTriggered: root.retryRequested()
            }
        }

        Button {
            Layout.alignment: Qt.AlignHCenter
            flat: true
            text: qsTr("Forget")
            icon.name: "edit-delete-remove-symbolic"
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Stop reconnecting this device. Its saved look is kept.")
            onClicked: root.forgetRequested()
        }
    }
}
