import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    id: panel

    property var deviceModel
    /** Root App facade (for isDeviceOpenInApp / disconnect). */
    property var appFacade
    property string lastError: ""
    property color errorTextColor: Kirigami.Theme.negativeTextColor
    property string devicesHint: ""

    signal refreshClicked()
    signal connectRequested(string kind, int bus, int addr)
    signal clearErrorClicked()

    RowLayout {
        Layout.leftMargin: Kirigami.Units.largeSpacing
        Layout.rightMargin: Kirigami.Units.largeSpacing
        Layout.topMargin: Kirigami.Units.smallSpacing
        Button {
            text: qsTr("Refresh list")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Rescan USB for keyboard (ITE 8291) and LED bar (ITE 8233).")
            onClicked: panel.refreshClicked()
        }
        Label {
            text: panel.devicesHint
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }

    Kirigami.InlineMessage {
        objectName: "deviceErrorInline"
        Layout.fillWidth: true
        Layout.leftMargin: Kirigami.Units.largeSpacing
        Layout.rightMargin: Kirigami.Units.largeSpacing
        visible: panel.lastError.length > 0
        type: Kirigami.MessageType.Error
        text: panel.lastError
        actions: [
            Kirigami.Action {
                text: qsTr("Clear error")
                icon.name: "edit-clear-symbolic"
                onTriggered: panel.clearErrorClicked()
            }
        ]
    }

    Item {
        Layout.fillWidth: true
        Layout.fillHeight: true

        Column {
            id: deviceColumn
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.largeSpacing

            Repeater {
                model: panel.deviceModel

                delegate: Item {
                    id: deviceRow
                    width: deviceColumn.width
                    implicitHeight: rowLayout.implicitHeight + Kirigami.Units.largeSpacing * 2
                    height: implicitHeight

                    readonly property bool openInApp: {
                        if (!panel.appFacade)
                            return false
                        var _ = panel.appFacade.deviceConnectionEpoch
                        return panel.appFacade.isDeviceOpenInApp(model.kind, model.bus, model.addr)
                    }

                    Rectangle {
                        anchors.fill: parent
                        radius: Kirigami.Units.smallSpacing
                        color: Kirigami.Theme.alternateBackgroundColor
                        border.width: 1
                        border.color: Qt.alpha(Kirigami.Theme.disabledTextColor, 0.22)
                    }

                    RowLayout {
                        id: rowLayout
                        anchors {
                            left: parent.left
                            right: parent.right
                            top: parent.top
                            margins: Kirigami.Units.largeSpacing
                        }
                        spacing: Kirigami.Units.largeSpacing

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            spacing: Kirigami.Units.smallSpacing

                            Label {
                                text: model.label
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                /** Same metrics in both states; colour indicates “open in app”. */
                                font.weight: Font.Normal
                                color: deviceRow.openInApp ? Kirigami.Theme.linkColor : Kirigami.Theme.textColor
                            }
                            Label {
                                text: qsTr("Open in this app — use the Keyboard or LED bar tab.")
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                font.pointSize: 9
                                /** Invisible when disconnected but still laid out — no card height jump on connect. */
                                opacity: deviceRow.openInApp ? 0.9 : 0
                                color: Kirigami.Theme.textColor
                            }
                        }
                        Button {
                            text: deviceRow.openInApp ? qsTr("Disconnect") : qsTr("Connect")
                            highlighted: deviceRow.openInApp
                            Layout.alignment: Qt.AlignTop
                            Layout.minimumWidth: Kirigami.Units.gridUnit * 11
                            Layout.preferredHeight: implicitHeight
                            ToolTip.visible: hovered
                            ToolTip.text: deviceRow.openInApp
                                           ? qsTr("Release the USB handle for this device in the GUI.")
                                           : qsTr("Claim this USB device for Keyboard or LED bar controls.")
                            onClicked: {
                                if (deviceRow.openInApp)
                                    panel.appFacade.disconnectDeviceKind(model.kind)
                                else
                                    panel.connectRequested(model.kind, model.bus, model.addr)
                            }
                        }
                    }
                }
            }
        }

        Label {
            anchors.centerIn: parent
            width: parent.width - Kirigami.Units.gridUnit * 8
            visible: panel.deviceModel && panel.deviceModel.count === 0
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            opacity: 0.75
            text: qsTr("No supported devices found.\n\nCheck that the keyboard or LED bar is plugged in, then try Refresh. If devices appear but Connect fails, you may need udev rules or run as root — see README.")
        }
    }
}
