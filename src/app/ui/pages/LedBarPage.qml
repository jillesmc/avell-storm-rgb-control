import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kirigami.layouts as KLayouts
import components

/**
 * LED bar: headers + scroll body by subNavIndex + footer (shell drives subNavIndex).
 */
Item {
    id: ledRoot
    objectName: "ledBarPage"
    property var appShell
    property int subNavIndex: 0

    property bool ledPreferNamed: true
    property string ledPickName: ""
    property bool ledHexProgrammatic: false

    function applyLedConfiguration() {
        var m = ledRoot.subNavIndex
        if (m === 0) {
            if (ledRoot.ledPreferNamed && ledRoot.ledPickName.length > 0)
                App.ledBar.setColorFromSpec(ledRoot.ledPickName)
            else
                App.ledBar.setColorFromSpec(ledHex.text)
        } else if (m === 1) {
            App.ledBar.applyPalette(appShell.ledSelectedPalette, ledPalFx.currentText)
        } else if (m === 2) {
            App.ledBar.applyEffect(appShell.ledSelectedEffect)
        } else if (m === 3) {
            App.ledBar.applyBrightnessSpeedEffect(
                ledGlobalBright.value,
                ledTuneSpeed.value,
                ledTuneFx.currentText
            )
        }
    }

    function ledInfoSummary() {
        if (!App.ledBar.connected)
            return qsTr("Not connected. Turn on the sidebar switch or choose a device on Devices.")
        return App.ledBar.infoText.length > 0 ? App.ledBar.infoText : qsTr("Tap Refresh in this panel for device details.")
    }

    function setHexFromNamed(r, g, b) {
        ledRoot.ledHexProgrammatic = true
        var h = function (v) {
            var s = Math.round(v).toString(16)
            return s.length === 1 ? "0" + s : s
        }
        ledHex.text = "#" + h(r) + h(g) + h(b)
        ledRoot.ledHexProgrammatic = false
    }

    Component.onCompleted: {
        if (ledRoot.ledPickName.length === 0 && App.ledNamedColors.length > 0)
            ledRoot.ledPickName = App.ledNamedColors[0]
        if (App.ledNamedColorEntries.length > 0) {
            var e = App.ledNamedColorEntries[0]
            ledRoot.setHexFromNamed(e.r, e.g, e.b)
        }
    }

    Item {
        anchors.fill: parent
        anchors.leftMargin: Kirigami.Units.largeSpacing
        anchors.rightMargin: Kirigami.Units.largeSpacing
        anchors.topMargin: Kirigami.Units.largeSpacing
        anchors.bottomMargin: Kirigami.Units.largeSpacing

        ColumnLayout {
            anchors.fill: parent
            spacing: Kirigami.Units.largeSpacing

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Kirigami.Heading {
                        level: 3
                        text: qsTr("LED bar")
                    }
                    ToolButton {
                        icon.name: "dialog-information-symbolic"
                        onClicked: ledInfoPopup.open()
                    }
                    Popup {
                        id: ledInfoPopup
                        width: Math.min(ledRoot.width - Kirigami.Units.gridUnit * 4, 420)
                        padding: Kirigami.Units.mediumSpacing
                        modal: true
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                        contentItem: ColumnLayout {
                            spacing: Kirigami.Units.smallSpacing
                            width: ledInfoPopup.availableWidth
                            Label {
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                text: ledInfoSummary()
                            }
                            RowLayout {
                                spacing: Kirigami.Units.smallSpacing
                                Button {
                                    text: qsTr("Refresh")
                                    onClicked: App.ledBar.refreshInspect()
                                }
                                Button {
                                    text: qsTr("Disconnect")
                                    enabled: App.ledBar.connected
                                    onClicked: App.ledBar.disconnectDevice()
                                }
                            }
                        }
                    }
                    Item {
                        Layout.fillWidth: true
                    }
                    Label {
                        text: qsTr("Connected")
                        visible: App.ledBar.connected
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    SliderSpinRow {
                        id: ledGlobalBright
                        label: qsTr("Brightness 0–100")
                        from: 0
                        to: 100
                        value: 50
                        Layout.fillWidth: true
                        sliderMinimumWidth: 100
                    }
                    Button {
                        text: qsTr("Set brightness + effect")
                        ToolTip.visible: hovered
                        ToolTip.text: qsTr("Set brightness and re-apply the selected effect.")
                        enabled: App.ledBar.connected
                        onClicked: App.ledBar.setBrightnessWithEffect(ledGlobalBright.value, ledQuickBriFx.currentText)
                    }
                    ComboBox {
                        id: ledQuickBriFx
                        model: App.ledEffectNames
                        Layout.preferredWidth: 160
                        Component.onCompleted: syncQuickFx()
                        onModelChanged: syncQuickFx()
                        function syncQuickFx() {
                            var names = App.ledEffectNames
                            var sel = appShell.ledSelectedEffect
                            for (var j = 0; j < names.length; j++) {
                                if (names[j] === sel) {
                                    currentIndex = j
                                    return
                                }
                            }
                            if (names.length > 0)
                                currentIndex = 0
                        }
                        onActivated: function (ix) {
                            appShell.ledSelectedEffect = textAt(ix)
                        }
                    }
                    Connections {
                        target: appShell
                        function onLedSelectedEffectChanged() {
                            ledQuickBriFx.syncQuickFx()
                        }
                    }
                }
            }

        Kirigami.Separator {
            Layout.fillWidth: true
        }

        ScrollView {
            id: ledScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            StackLayout {
                id: ledModeStack
                width: Math.max(ledScroll.availableWidth, 200)
                currentIndex: ledRoot.subNavIndex
                implicitHeight: {
                    var it = ledModeStack.itemAt(ledModeStack.currentIndex)
                    return it ? it.implicitHeight : Kirigami.Units.gridUnit * 20
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    width: parent.width
                    Layout.leftMargin: Kirigami.Units.smallSpacing
                    Layout.rightMargin: Kirigami.Units.smallSpacing
                    Label {
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        text: qsTr("Named swatches and hex are both visible. Apply uses a named key if you last tapped a swatch; editing hex switches to hex apply.")
                        font.italic: true
                    }
                    Label {
                        text: qsTr("Named colours (LED table)")
                    }
                    Flow {
                        id: ledNamedFlow
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing
                        Repeater {
                            model: App.ledNamedColorEntries
                            delegate: Rectangle {
                                required property var modelData
                                width: (ledNamedFlow.width - ledNamedFlow.spacing * 3) / 4
                                height: Kirigami.Units.gridUnit * 5
                                radius: 4
                                border.width: ledRoot.ledPreferNamed && ledRoot.ledPickName === modelData.name ? 3 : 1
                                border.color: ledRoot.ledPreferNamed && ledRoot.ledPickName === modelData.name
                                              ? Kirigami.Theme.highlightColor
                                              : Qt.alpha(Kirigami.Theme.disabledTextColor, 0.22)
                                color: Qt.rgba(modelData.r / 255, modelData.g / 255, modelData.b / 255, 1)
                                Label {
                                    anchors.bottom: parent.bottom
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    anchors.margins: 2
                                    text: modelData.name
                                    font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                                    style: Text.Outline
                                    styleColor: Qt.rgba(0, 0, 0, 0.7)
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        ledRoot.ledPreferNamed = true
                                        ledRoot.ledPickName = modelData.name
                                        ledRoot.setHexFromNamed(modelData.r, modelData.g, modelData.b)
                                    }
                                }
                            }
                        }
                    }
                    Label {
                        text: qsTr("Hex (#RRGGBB)")
                    }
                    TextField {
                        id: ledHex
                        placeholderText: "#ff5500"
                        Layout.preferredWidth: 140
                        ToolTip.visible: hovered
                        ToolTip.text: qsTr("CSS-style #RRGGBB")
                        onTextChanged: {
                            if (!ledRoot.ledHexProgrammatic)
                                ledRoot.ledPreferNamed = false
                        }
                    }
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    width: parent.width
                    Label {
                        text: qsTr("Preset (tap chip)")
                        Layout.leftMargin: Kirigami.Units.smallSpacing
                    }
                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: Kirigami.Units.smallSpacing
                        Layout.rightMargin: Kirigami.Units.smallSpacing
                        spacing: Kirigami.Units.smallSpacing
                        Repeater {
                            model: App.ledPalettePresets
                            delegate: Kirigami.Chip {
                                required property var modelData
                                closable: false
                                text: modelData
                                checked: appShell.ledSelectedPalette === modelData
                                ToolTip.visible: hovered
                                ToolTip.text: qsTr("Preset palette: %1").arg(modelData)
                                onClicked: appShell.ledSelectedPalette = modelData
                            }
                        }
                    }
                    ComboBox {
                        id: ledPalFx
                        model: App.ledEffectNames
                        Layout.fillWidth: true
                        Layout.leftMargin: Kirigami.Units.smallSpacing
                        Layout.rightMargin: Kirigami.Units.smallSpacing
                        ToolTip.visible: hovered
                        ToolTip.text: qsTr("Visual effect paired with the chosen preset colours.")
                    }
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    width: parent.width
                    Label {
                        text: qsTr("Effect (tap a chip to select)")
                        Layout.leftMargin: Kirigami.Units.smallSpacing
                    }
                    GridView {
                        id: ledFxGrid
                        objectName: "ledBarEffectGrid"
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.ceil(App.ledEffectNames.length / 2) * (Kirigami.Units.gridUnit * 5 + Kirigami.Units.smallSpacing)
                            + Kirigami.Units.smallSpacing
                        Layout.leftMargin: Kirigami.Units.smallSpacing
                        Layout.rightMargin: Kirigami.Units.smallSpacing
                        clip: false
                        cellWidth: Math.max(width / 2, Kirigami.Units.gridUnit * 14)
                        cellHeight: Kirigami.Units.gridUnit * 5 + Kirigami.Units.smallSpacing
                        model: App.ledEffectNames
                        delegate: EffectCard {
                            width: ledFxGrid.cellWidth - 6
                            height: ledFxGrid.cellHeight - 6
                            required property int index
                            effectName: App.ledEffectNames[index]
                            selected: appShell.ledSelectedEffect === effectName
                            onActivated: appShell.ledSelectedEffect = effectName
                        }
                    }
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    width: parent.width
                    KLayouts.FormLayout {
                        wideMode: true
                        Layout.fillWidth: true
                        Layout.leftMargin: Kirigami.Units.smallSpacing
                        Layout.rightMargin: Kirigami.Units.smallSpacing
                        Label {
                            Kirigami.FormData.label: qsTr("Note:")
                            text: qsTr("Brightness is set from the bar above; this mode applies speed and effect together.")
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        SliderSpinRow {
                            id: ledTuneSpeed
                            showLabel: false
                            Kirigami.FormData.label: qsTr("Speed (1–10):")
                            from: 1
                            to: 10
                            value: 3
                        }
                        ComboBox {
                            id: ledTuneFx
                            model: App.ledEffectNames
                            Kirigami.FormData.label: qsTr("Effect:")
                            Layout.fillWidth: true
                            ToolTip.visible: hovered
                            ToolTip.text: qsTr("Effect applied after brightness and speed.")
                        }
                    }
                }
            }
        }

        Kirigami.Separator {
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            Button {
                text: qsTr("Power off")
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Turn LED bar off. Last applied look is stored for Power on.")
                enabled: App.ledBar.connected
                onClicked: App.ledBar.powerOff()
            }
            Button {
                text: qsTr("Power on")
                ToolTip.visible: hovered
                ToolTip.text: App.ledBar.replayPowerOnAvailable
                              ? qsTr("Initialize the bar and restore the last applied colours / effect.")
                              : qsTr("Apply a configuration first, then Power off, to enable replay.")
                enabled: App.ledBar.connected && App.ledBar.replayPowerOnAvailable
                onClicked: App.ledBar.powerOnReplay()
            }
            Item {
                Layout.fillWidth: true
            }
            Button {
                objectName: "ledBarApplyConfig"
                text: qsTr("Apply")
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Apply the current LED bar mode.")
                enabled: App.ledBar.connected
                onClicked: ledRoot.applyLedConfiguration()
            }
        }
        }
    }
}
