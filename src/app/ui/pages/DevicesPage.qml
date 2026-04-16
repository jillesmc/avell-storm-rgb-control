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
            devicesHint: qsTr("Select a device, then Connect. USB access usually needs udev rules or root — see README.")
            showHeaderRefresh: false
            onRefreshClicked: App.refreshDevices()
            onConnectRequested: function (kind, bus, addr) {
                App.connectDevice(kind, bus, addr)
            }
            onClearErrorClicked: App.state.clearError()
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
