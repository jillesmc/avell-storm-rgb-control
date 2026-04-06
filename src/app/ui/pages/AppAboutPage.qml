import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

/**
 * About + app preferences (tray quit lives here).
 */
Kirigami.ScrollablePage {
    id: aboutRoot
    objectName: "aboutPage"
    title: ""

    ColumnLayout {
        width: aboutRoot.width - aboutRoot.leftPadding - aboutRoot.rightPadding
        spacing: Kirigami.Units.largeSpacing

        Kirigami.AboutItem {
            id: aboutItem
            Layout.fillWidth: true
            wideMode: aboutRoot.width >= implicitWidth
            aboutData: ({
                displayName: "Avell Storm RGB",
                productName: "avell-storm-rgb",
                componentName: "avell-storm-rgb",
                shortDescription: qsTr("ITE 8291 keyboard + ITE 8233 LED bar control"),
                homepage: "",
                bugAddress: "",
                version: App.applicationVersion,
                otherText: "",
                authors: [],
                credits: [],
                translators: [],
                licenses: [
                    {
                        name: "GPL-2.0-or-later",
                        spdx: "GPL-2.0-or-later",
                        text: ""
                    }
                ],
                copyrightStatement: qsTr("GPL-2.0-or-later — LICENSE and NOTICE."),
                desktopFileName: ""
            })
        }

        Kirigami.Separator { Layout.fillWidth: true }

        Kirigami.Heading {
            Layout.fillWidth: true
            level: 3
            text: qsTr("Settings")
        }

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

        Button {
            text: qsTr("Quit application")
            onClicked: App.quitApplication()
        }
    }
}
