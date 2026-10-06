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
    /** When false, hide the top “Refresh list” row (shell puts Refresh in a footer). */
    property bool showHeaderRefresh: true

    signal refreshClicked()
    signal connectRequested(string kind, int bus, int addr)
    signal clearErrorClicked()

    Flow {
        visible: panel.showHeaderRefresh
        Layout.fillWidth: true
        Layout.leftMargin: Kirigami.Units.largeSpacing
        Layout.rightMargin: Kirigami.Units.largeSpacing
        Layout.topMargin: Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.mediumSpacing
        spacing: Kirigami.Units.smallSpacing
        Button {
            text: qsTr("Refresh list")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Rescan USB for keyboard (ITE 8291) and LED bar (ITE 8233).")
            onClicked: panel.refreshClicked()
        }
        Label {
            width: panel.width - Kirigami.Units.gridUnit * 12
            text: panel.devicesHint
            wrapMode: Text.WordWrap
        }
    }
    RowLayout {
        visible: !panel.showHeaderRefresh
        Layout.leftMargin: Kirigami.Units.largeSpacing
        Layout.rightMargin: Kirigami.Units.largeSpacing
        Layout.topMargin: Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.mediumSpacing
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
        Layout.bottomMargin: Kirigami.Units.mediumSpacing
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

        ScrollView {
            id: deviceScroll
            anchors.fill: parent
            clip: true

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
            }
            ScrollBar.horizontal: ScrollBar {
                policy: ScrollBar.AlwaysOff
            }

            Item {
                id: deviceScrollContent
                width: deviceScroll.availableWidth
                implicitHeight: deviceColumn.implicitHeight

                Column {
                    id: deviceColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
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

                            GridLayout {
                                id: rowLayout
                                anchors {
                                    left: parent.left
                                    right: parent.right
                                    top: parent.top
                                    margins: Kirigami.Units.largeSpacing
                                }
                                columns: width < Kirigami.Units.gridUnit * 24 ? 1 : 2
                                rowSpacing: Kirigami.Units.largeSpacing
                                columnSpacing: Kirigami.Units.largeSpacing

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
                                        text: qsTr("Remembered — configure it from the sidebar.")
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
                                    Layout.alignment: rowLayout.columns === 1 ? Qt.AlignLeft : Qt.AlignTop
                                    Layout.minimumWidth: Kirigami.Units.gridUnit * 11
                                    Layout.preferredHeight: implicitHeight
                                    ToolTip.visible: hovered
                                    ToolTip.text: deviceRow.openInApp
                                                   ? qsTr("Disconnect and forget this device. Its saved look is kept.")
                                                   : qsTr("Connect and remember this device. It reconnects when the app opens.")
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
            }
        }

        Label {
            z: 1
            anchors.centerIn: parent
            width: parent.width - Kirigami.Units.gridUnit * 8
            visible: !panel.deviceModel || panel.deviceModel.count === 0
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            opacity: 0.75
            text: qsTr("No supported devices found.\n\nCheck that the keyboard or LED bar is plugged in, then try Refresh. If devices appear but Connect fails, you may need udev rules or run as root — see README.")
        }
    }
}
