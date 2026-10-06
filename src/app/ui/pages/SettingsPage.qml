import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.Page {
    id: settingsRoot
    objectName: "settingsPage"
    title: ""

    onVisibleChanged: {
        if (visible)
            App.refreshLaunchAtLogin()
    }

    leftPadding: Kirigami.Units.largeSpacing
    rightPadding: Kirigami.Units.largeSpacing
    topPadding: Kirigami.Units.largeSpacing

    background: Rectangle {
        color: "transparent"
    }

    ScrollView {
        id: settingsScroll
        anchors.fill: parent
        clip: true

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
        }
        ScrollBar.horizontal: ScrollBar {
            policy: ScrollBar.AlwaysOff
        }

        Item {
            width: settingsScroll.availableWidth
            implicitHeight: settingsColumn.implicitHeight

            ColumnLayout {
                id: settingsColumn
                width: parent.width
                spacing: Kirigami.Units.largeSpacing

                Kirigami.Heading {
                    level: 2
                    text: qsTr("Application")
                    Layout.fillWidth: true
                }
                Kirigami.Separator { Layout.fillWidth: true }

                CheckBox {
                    text: qsTr("Close to system tray (hide window instead of quitting)")
                    checked: App.closeToTray
                    onToggled: App.closeToTray = checked
                    ToolTip.visible: hovered
                    ToolTip.text: qsTr("Quit fully from the tray menu (Quit) or the button below.")
                    Layout.fillWidth: true
                }

                CheckBox {
                    text: qsTr("Auto-connect keyboard and LED bar when the app starts (after USB scan)")
                    checked: App.autoConnectOnStartup
                    onToggled: App.autoConnectOnStartup = checked
                    ToolTip.visible: hovered
                    ToolTip.text: qsTr("Uses the first matching device of each type from the device list. Disable if you prefer to connect manually on the Devices tab.")
                    Layout.fillWidth: true
                }

                CheckBox {
                    objectName: "launchAtLoginCheck"
                    text: qsTr("Start at login (system tray only)")
                    checked: App.launchAtLogin
                    onToggled: App.launchAtLogin = checked
                    ToolTip.visible: hovered
                    ToolTip.text: qsTr("Adds an entry under ~/.config/autostart so the app launches hidden in the tray when you log in.")
                    Layout.fillWidth: true
                }

                Kirigami.InlineMessage {
                    objectName: "settingsErrorInline"
                    Layout.fillWidth: true
                    visible: App.settingsError.length > 0
                    type: Kirigami.MessageType.Error
                    text: App.settingsError
                    actions: [
                        Kirigami.Action {
                            text: qsTr("Clear error")
                            icon.name: "edit-clear-symbolic"
                            onTriggered: App.clearSettingsError()
                        }
                    ]
                }

                Kirigami.Separator { Layout.fillWidth: true }

                Kirigami.Heading {
                    level: 3
                    text: qsTr("Keyboard diagnostics")
                    Layout.fillWidth: true
                }
                CheckBox {
                    text: qsTr("Verbose USB for keyboard (reconnect required)")
                    checked: App.keyboard.debugUsb
                    onToggled: function (c) { App.keyboard.debugUsb = c }
                    ToolTip.visible: hovered
                    ToolTip.text: qsTr("Enables verbose USB logging when opening the keyboard device.")
                    Layout.fillWidth: true
                }

                Button {
                    text: qsTr("Quit application")
                    onClicked: App.quitApplication()
                }
            }
        }
    }
}
