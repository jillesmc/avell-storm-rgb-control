import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import components

/**
 * Devices: USB list; Refresh is in the footer when used inside the KDE-style shell.
 */
Kirigami.Page {
    id: devicesRoot
    objectName: "devicesPage"
    title: ""

    background: Rectangle {
        color: "transparent"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Kirigami.Units.largeSpacing

        DeviceListPanel {
            objectName: "deviceListPanelRoot"
            Layout.fillWidth: true
            Layout.fillHeight: true
            appFacade: App
            deviceModel: App.devices
            lastError: App.state.lastError
            devicesHint: qsTr("Connect a device to remember it. USB access usually needs udev rules — see README.")
            showHeaderRefresh: false
            onRefreshClicked: App.refreshDevices()
            onConnectRequested: function (kind, bus, addr) {
                App.connectDevice(kind, bus, addr)
            }
            onClearErrorClicked: App.state.clearError()
        }

        /* Absent (not just hidden) without the optional tuya extra (BR-17). */
        Loader {
            Layout.fillWidth: true
            Layout.leftMargin: Kirigami.Units.largeSpacing
            Layout.rightMargin: Kirigami.Units.largeSpacing
            active: App.bulbsAvailable
            visible: active
            sourceComponent: BulbListPanel {}
        }

        Kirigami.Separator { Layout.fillWidth: true }

        Flow {
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.largeSpacing
            Button {
                objectName: "devicesFooterRefresh"
                text: qsTr("Refresh list")
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Rescan USB for keyboard (ITE 8291) and LED bar (ITE 8233).")
                onClicked: App.refreshDevices()
            }
        }
    }
}
