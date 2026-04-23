import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kirigami.delegates as KirigamiDelegates
import org.kde.kirigami.primitives as KirigamiPrimitives
import components
import pages

Kirigami.ApplicationWindow {
    id: appRoot
    width: 1100
    height: 800
    visible: true
    title: qsTr("Avell Storm RGB")

    /**
     * Plasma System Settings-style depth: col1 darkest → col2 base → col3 lightest.
     * Uses theme background so light/dark sessions stay coherent.
     */
    /** Avoid Qt.darker/Qt.lighter — not in all QML Qt builds; ColorUtils is Kirigami-stable. */
    readonly property color shellPrimarySidebar: Kirigami.ColorUtils.linearInterpolation(
        Kirigami.Theme.backgroundColor,
        Qt.rgba(0, 0, 0, 1),
        0.2
    )
    readonly property color shellSubNavBg: Kirigami.Theme.backgroundColor
    readonly property color shellContentBg: Kirigami.ColorUtils.linearInterpolation(
        Kirigami.Theme.backgroundColor,
        Kirigami.Theme.textColor,
        0.075
    )
    /** Reliable on minimal/offscreen QPA themes (separatorColor may be undefined there). */
    readonly property color shellDividerColor: Kirigami.ColorUtils.linearInterpolation(
        Kirigami.Theme.backgroundColor,
        Kirigami.Theme.textColor,
        0.22
    )

    /** 0 Devices, 1 Keyboard, 2 LED bar, 3 Settings, 4 About */
    property int primarySection: 0
    property int keyboardSubNavIndex: 0
    property int ledSubNavIndex: 0

    property string selectedKeyboardEffect: ""
    property string ledSelectedPalette: ""
    property string ledSelectedEffect: ""

    onClosing: function (close) {
        if (App.closeToTray) {
            close.accepted = false
            appRoot.visible = false
        }
    }

    function syncPrimarySidebarListIndex() {
        if (appRoot.primarySection <= 2) {
            for (var i = 0; i < primaryNavModel.count; i++) {
                if (primaryNavModel.get(i).page === appRoot.primarySection) {
                    primarySidebarList.currentIndex = i
                    return
                }
            }
        } else {
            primarySidebarList.currentIndex = -1
        }
    }

    function fillKeyboardSubNavModel() {
        keyboardSubNavModel.clear()
        keyboardSubNavModel.append({ rowKind: "header", headerText: qsTr("Firmware"), itemText: "", page: -1 })
        keyboardSubNavModel.append({ rowKind: "item", headerText: "", itemText: qsTr("Effect"), page: 0 })
        keyboardSubNavModel.append({ rowKind: "item", headerText: "", itemText: qsTr("Palette slot configuration"), page: 1 })
        keyboardSubNavModel.append({ rowKind: "header", headerText: qsTr("User-defined"), itemText: "", page: -1 })
        keyboardSubNavModel.append({ rowKind: "item", headerText: "", itemText: qsTr("Solid color"), page: 2 })
        keyboardSubNavModel.append({ rowKind: "item", headerText: "", itemText: qsTr("Per-key grid"), page: 3 })
        keyboardSubNavModel.append({ rowKind: "item", headerText: "", itemText: qsTr("Animation file"), page: 4 })
        keyboardSubNavModel.append({ rowKind: "item", headerText: "", itemText: qsTr("Follow screen"), page: 5 })
        keyboardSubNavModel.append({ rowKind: "header", headerText: qsTr("Extra"), itemText: "", page: -1 })
        keyboardSubNavModel.append({ rowKind: "item", headerText: "", itemText: qsTr("Tools"), page: 6 })
    }

    function syncKeyboardSubNavListHighlight() {
        var i
        for (i = 0; i < keyboardSubNavModel.count; i++) {
            var row = keyboardSubNavModel.get(i)
            if (row.rowKind === "item" && row.page === appRoot.keyboardSubNavIndex) {
                if (keyboardSubNavList.currentIndex !== i)
                    keyboardSubNavList.currentIndex = i
                keyboardSubNavList.positionViewAtIndex(i, ListView.Contain)
                return
            }
        }
        keyboardSubNavList.currentIndex = -1
    }

    Component.onCompleted: {
        App.refreshDevices()
        App.tryAutoConnectDiscoveredDevices()
        if (App.keyboardEffectNames.length > 0)
            selectedKeyboardEffect = App.keyboardEffectNames[0]
        if (App.ledPalettePresets.length > 0)
            ledSelectedPalette = App.ledPalettePresets[0]
        if (App.ledEffectNames.length > 0)
            ledSelectedEffect = App.ledEffectNames[0]

        primaryNavModel.append({
            sectionName: "devices",
            title: qsTr("Devices"),
            iconName: "computer-laptop-symbolic",
            page: 0,
            showChevron: false,
            showSwitch: false
        })
        primaryNavModel.append({
            sectionName: "enabled",
            title: qsTr("Keyboard"),
            iconName: "input-keyboard-symbolic",
            page: 1,
            showChevron: true,
            showSwitch: true
        })
        primaryNavModel.append({
            sectionName: "enabled",
            title: qsTr("LED bar"),
            iconName: "keyboard-spacebar",
            page: 2,
            showChevron: true,
            showSwitch: true
        })
        primarySidebarList.currentIndex = 0

        appRoot.fillKeyboardSubNavModel()
        Qt.callLater(function () {
            appRoot.syncKeyboardSubNavListHighlight()
        })
    }

    Connections {
        target: appRoot
        function onPrimarySectionChanged() {
            syncPrimarySidebarListIndex()
        }
    }

    ListModel {
        id: primaryNavModel
    }

    ListModel {
        id: keyboardSubNavModel
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 1
            Layout.fillHeight: true
            color: appRoot.shellDividerColor
        }

        Item {
            Layout.preferredWidth: Math.round(Kirigami.Units.gridUnit * 11)
            Layout.fillHeight: true
            Layout.minimumWidth: Math.round(Kirigami.Units.gridUnit * 10)

            Rectangle {
                anchors.fill: parent
                color: appRoot.shellPrimarySidebar
            }

            ColumnLayout {
                id: primarySidebarColumn
                anchors.fill: parent
                spacing: 0

                ListView {
                    id: primarySidebarList
                    objectName: "primarySidebar"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 0
                    boundsBehavior: Flickable.StopAtBounds
                    model: primaryNavModel

                    currentIndex: 0
                    highlightMoveDuration: 0

                    section.property: "sectionName"
                    section.criteria: ViewSection.FullString
                    /** Same row as Kirigami / Plasma settings: section title + horizontal rule. */
                    section.delegate: Column {
                        width: primarySidebarList.width
                        spacing: 0

                        Item {
                            width: parent.width
                            implicitHeight: section === "enabled"
                                          ? (enabledHdrRow.implicitHeight
                                             + Kirigami.Units.mediumSpacing
                                             + Kirigami.Units.largeSpacing)
                                          : 0
                            visible: section === "enabled"

                            RowLayout {
                                id: enabledHdrRow
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.topMargin: Kirigami.Units.mediumSpacing
                                anchors.leftMargin: Kirigami.Units.mediumSpacing
                                anchors.rightMargin: Kirigami.Units.smallSpacing
                                spacing: Kirigami.Units.mediumSpacing

                                Label {
                                    text: qsTr("Enabled devices")
                                    color: Kirigami.Theme.disabledTextColor
                                    font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                                    font.bold: true
                                    elide: Text.ElideRight
                                    Layout.alignment: Qt.AlignVCenter
                                }
                                Kirigami.Separator {
                                    Layout.fillWidth: true
                                    Layout.alignment: Qt.AlignVCenter
                                }
                            }
                        }

                        Item {
                            width: parent.width
                            height: section === "devices" ? Kirigami.Units.largeSpacing : 0
                        }
                    }

                    delegate: ItemDelegate {
                        width: ListView.view.width
                        text: ""
                        icon.name: ""
                        topPadding: Kirigami.Units.mediumSpacing
                        bottomPadding: Kirigami.Units.mediumSpacing
                        leftPadding: Kirigami.Units.mediumSpacing
                        rightPadding: Kirigami.Units.smallSpacing

                        contentItem: RowLayout {
                            spacing: Kirigami.Units.smallSpacing
                            KirigamiPrimitives.Icon {
                                source: model.iconName
                                implicitWidth: Kirigami.Units.iconSizes.small
                                implicitHeight: Kirigami.Units.iconSizes.small
                                isMask: true
                                color: Kirigami.Theme.textColor
                                fallback: "applications-other"
                            }
                            Label {
                                text: model.title
                                Layout.fillWidth: true
                                color: Kirigami.Theme.textColor
                                elide: Text.ElideRight
                                horizontalAlignment: Text.AlignLeft
                            }
                            Label {
                                text: "›"
                                visible: model.showChevron
                                color: Kirigami.Theme.disabledTextColor
                                font.pointSize: Kirigami.Theme.defaultFont.pointSize + 1
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Switch {
                                visible: model.showSwitch
                                checked: model.page === 1 ? App.keyboard.connected : App.ledBar.connected
                                scale: 0.9
                                transformOrigin: Item.Center
                                Layout.alignment: Qt.AlignVCenter
                                onToggled: function (on) {
                                    if (model.page === 1) {
                                        if (on)
                                            App.connectFirstDiscovered("keyboard")
                                        else
                                            App.disconnectDeviceKind("keyboard")
                                    } else if (model.page === 2) {
                                        if (on)
                                            App.connectFirstDiscovered("led_bar")
                                        else
                                            App.disconnectDeviceKind("led_bar")
                                    }
                                }
                            }
                        }

                        onClicked: {
                            ListView.view.currentIndex = index
                            appRoot.primarySection = model.page
                            deviceContentStack.currentIndex = model.page
                        }
                    }

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                    }
                }

                Kirigami.Separator {
                    Layout.fillWidth: true
                    Layout.topMargin: Kirigami.Units.largeSpacing
                }

                Repeater {
                    model: [
                        {
                            title: qsTr("Settings"),
                            iconName: "preferences-system-symbolic",
                            page: 3
                        },
                        {
                            title: qsTr("About"),
                            iconName: "help-about-symbolic",
                            page: 4
                        }
                    ]
                    delegate: Item {
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: footerDelegate.implicitHeight
                        KirigamiDelegates.SubtitleDelegate {
                            id: footerDelegate
                            width: parent.width
                            text: modelData.title
                            icon.name: modelData.iconName
                            onClicked: {
                                appRoot.primarySection = modelData.page
                                deviceContentStack.currentIndex = modelData.page
                                primarySidebarList.currentIndex = -1
                            }
                        }
                        Rectangle {
                            anchors.fill: footerDelegate
                            z: -1
                            color: appRoot.primarySection === modelData.page
                                   ? Qt.alpha(Kirigami.Theme.highlightColor, 0.35)
                                   : "transparent"
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Kirigami.Units.mediumSpacing
                }
            }
        }

        Rectangle {
            Layout.preferredWidth: 1
            Layout.fillHeight: true
            color: appRoot.shellDividerColor
        }

        Item {
            Layout.preferredWidth: appRoot.primarySection === 1 ? Math.round(Kirigami.Units.gridUnit * 10.5) : 0
            Layout.fillHeight: true
            visible: appRoot.primarySection === 1
            Rectangle {
                anchors.fill: parent
                color: appRoot.shellSubNavBg
            }
            ListView {
                id: keyboardSubNavList
                objectName: "keyboardSubNav"
                anchors.fill: parent
                anchors.topMargin: Kirigami.Units.smallSpacing
                anchors.bottomMargin: Kirigami.Units.smallSpacing
                clip: true
                spacing: 0
                model: keyboardSubNavModel
                delegate: ColumnLayout {
                    width: ListView.view.width
                    spacing: 0

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: Kirigami.Units.mediumSpacing
                        Layout.bottomMargin: Kirigami.Units.smallSpacing
                        Layout.leftMargin: Kirigami.Units.mediumSpacing
                        Layout.rightMargin: Kirigami.Units.smallSpacing
                        visible: model.rowKind === "header"
                        spacing: Kirigami.Units.mediumSpacing

                        Label {
                            text: model.headerText
                            color: Kirigami.Theme.disabledTextColor
                            font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                            font.bold: true
                            elide: Text.ElideRight
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Kirigami.Separator {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                        }
                    }
                    ItemDelegate {
                        Layout.fillWidth: true
                        visible: model.rowKind === "item"
                        text: model.itemText
                        highlighted: ListView.isCurrentItem
                        topPadding: Kirigami.Units.mediumSpacing
                        bottomPadding: Kirigami.Units.mediumSpacing
                        leftPadding: Kirigami.Units.mediumSpacing
                        rightPadding: Kirigami.Units.mediumSpacing
                        onClicked: appRoot.keyboardSubNavIndex = model.page
                    }
                }
                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                }

                Connections {
                    target: appRoot
                    function onKeyboardSubNavIndexChanged() {
                        if (appRoot.primarySection === 1)
                            appRoot.syncKeyboardSubNavListHighlight()
                    }
                    function onPrimarySectionChanged() {
                        if (appRoot.primarySection === 1)
                            appRoot.syncKeyboardSubNavListHighlight()
                    }
                }
            }
        }

        Item {
            Layout.preferredWidth: appRoot.primarySection === 2 ? Math.round(Kirigami.Units.gridUnit * 10.5) : 0
            Layout.fillHeight: true
            visible: appRoot.primarySection === 2
            Rectangle {
                anchors.fill: parent
                color: appRoot.shellSubNavBg
            }
            ListView {
                id: ledSubNavList
                objectName: "ledSubNav"
                anchors.fill: parent
                anchors.topMargin: Kirigami.Units.smallSpacing
                anchors.bottomMargin: Kirigami.Units.smallSpacing
                clip: true
                spacing: 0
                model: [
                    qsTr("Color (named / hex)"),
                    qsTr("Preset + effect"),
                    qsTr("Effect only"),
                    qsTr("Brightness & motion")
                ]
                Component.onCompleted: currentIndex = appRoot.ledSubNavIndex
                onCurrentIndexChanged: {
                    if (appRoot.primarySection === 2 && currentIndex >= 0)
                        appRoot.ledSubNavIndex = currentIndex
                }
                delegate: ItemDelegate {
                    width: ListView.view.width
                    text: modelData
                    highlighted: ListView.isCurrentItem
                    topPadding: Kirigami.Units.mediumSpacing
                    bottomPadding: Kirigami.Units.mediumSpacing
                    leftPadding: Kirigami.Units.mediumSpacing
                    rightPadding: Kirigami.Units.mediumSpacing
                    onClicked: ListView.view.currentIndex = index
                }
                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                }

                Connections {
                    target: appRoot
                    function onLedSubNavIndexChanged() {
                        if (appRoot.primarySection === 2 && ledSubNavList.currentIndex !== appRoot.ledSubNavIndex)
                            ledSubNavList.currentIndex = appRoot.ledSubNavIndex
                    }
                    function onPrimarySectionChanged() {
                        if (appRoot.primarySection === 2)
                            ledSubNavList.currentIndex = appRoot.ledSubNavIndex
                    }
                }
            }
        }

        Rectangle {
            Layout.preferredWidth: (appRoot.primarySection === 1 || appRoot.primarySection === 2) ? 1 : 0
            Layout.fillHeight: true
            visible: appRoot.primarySection === 1 || appRoot.primarySection === 2
            color: appRoot.shellDividerColor
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Rectangle {
                anchors.fill: parent
                color: appRoot.shellContentBg
            }

            StackLayout {
                id: deviceContentStack
                objectName: "deviceContentStack"
                anchors.fill: parent
                currentIndex: 0

                DevicesPage {}

                KeyboardPage {
                    appShell: appRoot
                    subNavIndex: appRoot.keyboardSubNavIndex
                }

                LedBarPage {
                    appShell: appRoot
                    subNavIndex: appRoot.ledSubNavIndex
                }

                SettingsPage {}

                AppAboutPage {}
            }
        }
    }

    BusyOverlay {
        parent: Overlay.overlay
        anchors.fill: parent
        busy: App.state.busy
    }
}
