import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import components

/**
 * Devices tab: USB list + errors (scroll lives inside DeviceListPanel).
 */
Kirigami.Page {
    id: devicesRoot
    objectName: "devicesPage"
    title: ""

    DeviceListPanel {
        objectName: "deviceListPanelRoot"
        anchors.fill: parent
        appFacade: App
        deviceModel: App.devices
        lastError: App.state.lastError
        devicesHint: qsTr("Select a device, then Connect. USB access usually needs udev rules or root — see README.")
        onRefreshClicked: App.refreshDevices()
        onConnectRequested: function (kind, bus, addr) {
            App.connectDevice(kind, bus, addr)
        }
        onClearErrorClicked: App.state.clearError()
    }
}
