import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import components
import pages

Kirigami.ApplicationWindow {
    id: appRoot
    width: 1000
    height: 800
    visible: true
    title: qsTr("Avell Storm RGB")

    /** Stack indices: 0 Devices, 1 Keyboard, 2 LED bar, 3 About — fixed; tab bar indices are dynamic when actions are hidden. */
    function goToDevices() {
        mainStack.currentIndex = 0
        tabs.currentIndex = 0
    }

    onClosing: function (close) {
        if (App.closeToTray) {
            close.accepted = false
            appRoot.visible = false
        }
    }

    property string selectedKeyboardEffect: ""
    property string ledSelectedPalette: ""

    Component.onCompleted: {
        App.refreshDevices()
        App.tryAutoConnectDiscoveredDevices()
        if (App.keyboardEffectNames.length > 0)
            selectedKeyboardEffect = App.keyboardEffectNames[0]
        if (App.ledPalettePresets.length > 0)
            ledSelectedPalette = App.ledPalettePresets[0]
    }

    Connections {
        target: App.keyboard
        function onConnectedChanged() {
            if (!App.keyboard.connected && mainStack.currentIndex === 1)
                appRoot.goToDevices()
        }
    }

    Connections {
        target: App.ledBar
        function onConnectedChanged() {
            if (!App.ledBar.connected && mainStack.currentIndex === 2)
                appRoot.goToDevices()
        }
    }

    header: Kirigami.NavigationTabBar {
        id: tabs
        objectName: "mainNavTabs"
        actions: [
            Kirigami.Action {
                text: qsTr("Devices")
                icon.name: "computer-laptop-symbolic"
                checkable: true
                checked: true
                property int stackPage: 0
                onTriggered: mainStack.currentIndex = stackPage
            },
            Kirigami.Action {
                text: qsTr("Keyboard")
                icon.name: "input-keyboard-symbolic"
                checkable: true
                checked: false
                visible: App.keyboard.connected
                property int stackPage: 1
                onTriggered: mainStack.currentIndex = stackPage
            },
            Kirigami.Action {
                text: qsTr("LED bar")
                icon.name: "lightbulb-symbolic"
                checkable: true
                checked: false
                visible: App.ledBar.connected
                property int stackPage: 2
                onTriggered: mainStack.currentIndex = stackPage
            },
            Kirigami.Action {
                text: qsTr("About")
                icon.name: "help-about-symbolic"
                checkable: true
                checked: false
                property int stackPage: 3
                onTriggered: mainStack.currentIndex = stackPage
            }
        ]
    }

    StackLayout {
        id: mainStack
        objectName: "mainStack"
        anchors.fill: parent
        currentIndex: 0

        DevicesPage {}

        KeyboardPage {
            appShell: appRoot
        }

        LedBarPage {
            appShell: appRoot
        }

        AppAboutPage {}
    }

    BusyOverlay {
        parent: Overlay.overlay
        anchors.fill: parent
        busy: App.state.busy
    }
}
