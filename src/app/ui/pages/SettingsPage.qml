import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: settingsRoot
    objectName: "settingsPage"
    title: ""

    leftPadding: Kirigami.Units.largeSpacing
    rightPadding: Kirigami.Units.largeSpacing
    topPadding: Kirigami.Units.largeSpacing

    background: Rectangle {
        color: "transparent"
    }

    ColumnLayout {
        width: Math.max(
            settingsRoot.width - settingsRoot.leftPadding - settingsRoot.rightPadding,
            200
        )
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
            onToggled: function (c) { App.closeToTray = c }
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Quit fully from the tray menu (Quit) or the button below.")
        }

        CheckBox {
            text: qsTr("Auto-connect keyboard and LED bar when the app starts (after USB scan)")
            checked: App.autoConnectOnStartup
            onToggled: function (c) { App.autoConnectOnStartup = c }
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Uses the first matching device of each type from the device list. Disable if you prefer to connect manually on the Devices tab.")
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
        }

        Button {
            text: qsTr("Quit application")
            onClicked: App.quitApplication()
        }
    }
}
