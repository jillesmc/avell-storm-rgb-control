import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kirigami.layouts as KLayouts
import components

Kirigami.ScrollablePage {
    id: ledRoot
    objectName: "ledBarPage"
    property var appShell

    title: ""

    ColumnLayout {
        width: Math.max(ledRoot.width - Kirigami.Units.gridUnit * 6, 200)
        spacing: Kirigami.Units.largeSpacing
    Label {
        text: App.ledBar.connected ? qsTr("LED bar: connected") : qsTr("LED bar: not connected")
        font.bold: true
    }
    Button {
        text: qsTr("Disconnect LED bar")
        ToolTip.visible: hovered
        ToolTip.text: qsTr("Release USB handle for the LED bar.")
        enabled: App.ledBar.connected
        onClicked: App.ledBar.disconnectDevice()
    }
    RowLayout {
        Button {
            text: qsTr("Refresh status")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Same as CLI: avell-storm-rgb led-bar inspect")
            onClicked: App.ledBar.refreshInspect()
        }
    }
    Label { text: App.ledBar.infoText; wrapMode: Text.WordWrap; Layout.fillWidth: true }

    RowLayout {
        Button {
            text: qsTr("Power on")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("LED bar init / on sequence.")
            onClicked: App.ledBar.powerOn()
        }
        Button {
            text: qsTr("Power off")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Turn LED bar off.")
            onClicked: App.ledBar.powerOff()
        }
    }

    RowLayout {
        ComboBox {
            id: ledNamed
            model: App.ledNamedColors
            Layout.preferredWidth: 160
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Named colour from LED bar palette table.")
        }
        Button {
            text: qsTr("Named color")
            onClicked: App.ledBar.setColorFromSpec(ledNamed.currentText)
        }
        TextField {
            id: ledHex
            placeholderText: "#ff5500"
            Layout.preferredWidth: 120
            ToolTip.visible: hovered
            ToolTip.text: qsTr("CSS-style #RRGGBB")
        }
        Button {
            text: qsTr("Hex")
            onClicked: App.ledBar.setColorFromSpec(ledHex.text)
        }
    }

    Kirigami.Heading {
        level: 2
        text: qsTr("Palette preset + effect")
        Layout.fillWidth: true
    }
    Kirigami.Separator { Layout.fillWidth: true }
    Label { text: qsTr("Preset (tap chip)") }
    Flow {
        Layout.fillWidth: true
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
    RowLayout {
        Layout.fillWidth: true
        ComboBox {
            id: ledPalFx
            model: App.ledEffectNames
            Layout.fillWidth: true
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Visual effect paired with the chosen preset colours.")
        }
        Button {
            text: qsTr("Apply preset + effect")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Match CLI: led-bar palette … --with-effect …")
            onClicked: App.ledBar.applyPalette(appShell.ledSelectedPalette, ledPalFx.currentText)
        }
    }

    Kirigami.Heading {
        level: 2
        text: qsTr("Visual effect")
        Layout.fillWidth: true
    }
    Kirigami.Separator { Layout.fillWidth: true }
    GridView {
        id: ledFxGrid
        Layout.fillWidth: true
        height: Math.ceil(App.ledEffectNames.length / 2) * (Kirigami.Units.gridUnit * 5 + Kirigami.Units.smallSpacing)
            + Kirigami.Units.smallSpacing
        clip: false
        cellWidth: Math.max(width / 2, Kirigami.Units.gridUnit * 14)
        cellHeight: Kirigami.Units.gridUnit * 5 + Kirigami.Units.smallSpacing
        model: App.ledEffectNames
        delegate: EffectCard {
            width: ledFxGrid.cellWidth - 6
            height: ledFxGrid.cellHeight - 6
            required property int index
            effectName: App.ledEffectNames[index]
            onActivated: App.ledBar.applyEffect(effectName)
        }
    }
    Label {
        text: qsTr("Tap a chip to apply that effect.")
        font.pointSize: 9
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    KLayouts.FormLayout {
        Layout.fillWidth: true
        wideMode: true
        SliderSpinRow {
            id: ledBriRow
            showLabel: false
            Kirigami.FormData.label: qsTr("Brightness (0–100):")
            from: 0
            to: 100
            value: 50
        }
        RowLayout {
            Kirigami.FormData.label: qsTr("Re-apply effect:")
            spacing: Kirigami.Units.smallSpacing
            ComboBox {
                id: ledBriFx
                model: App.ledEffectNames
                Layout.fillWidth: true
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Re-apply this effect after setting brightness.")
            }
            Button {
                text: qsTr("Apply brightness + effect")
                ToolTip.visible: hovered
                ToolTip.text: qsTr("LED bar brightness 0–100 with effect (CLI parity).")
                onClicked: App.ledBar.setBrightnessWithEffect(ledBriRow.value, ledBriFx.currentText)
            }
        }
        SliderSpinRow {
            id: ledSpRow
            showLabel: false
            Kirigami.FormData.label: qsTr("Speed (1–10):")
            from: 1
            to: 10
            value: 3
        }
        RowLayout {
            Kirigami.FormData.label: qsTr("Re-apply effect:")
            spacing: Kirigami.Units.smallSpacing
            ComboBox {
                id: ledSpFx
                model: App.ledEffectNames
                Layout.fillWidth: true
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Re-apply this effect after setting motion speed.")
            }
            Button {
                text: qsTr("Apply speed + effect")
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Motion speed 1–10 with effect.")
                onClicked: App.ledBar.setSpeedWithEffect(ledSpRow.value, ledSpFx.currentText)
            }
        }
    }
    }
}

