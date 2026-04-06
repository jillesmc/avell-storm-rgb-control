import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kirigami.layouts as KLayouts
import QtQuick.Dialogs
import components

Kirigami.ScrollablePage {
    id: keyboardRoot
    objectName: "keyboardPage"
    property var appShell

    title: ""

    QtObject {
        id: gridPick
        property int row: -1
        property int col: -1
    }

    ColorDialog {
        id: kbGridColorDialog
        title: qsTr("Key cell color")
        onAccepted: {
            if (gridPick.row >= 0) {
                var c = kbGridColorDialog.selectedColor
                App.keyboard.setKeyCell(gridPick.row, gridPick.col,
                                        Math.round(c.r * 255),
                                        Math.round(c.g * 255),
                                        Math.round(c.b * 255), false)
            }
        }
    }

    ColorDialog {
        id: kbSolidColorDialog
        title: qsTr("Solid RGB")
        onAccepted: {
            var c = kbSolidColorDialog.selectedColor
            sr.value = Math.round(c.r * 255)
            sg.value = Math.round(c.g * 255)
            sb.value = Math.round(c.b * 255)
        }
    }

    ColorDialog {
        id: kbPaletteColorDialog
        title: qsTr("Palette slot RGB")
        onAccepted: {
            var c = kbPaletteColorDialog.selectedColor
            pr.value = Math.round(c.r * 255)
            pg.value = Math.round(c.g * 255)
            pb.value = Math.round(c.b * 255)
        }
    }

    FileDialog {
        id: kbAnimDialog
        title: qsTr("Animation script")
        fileMode: FileDialog.OpenFile
        nameFilters: [qsTr("Text (*.txt)"), qsTr("All (*)")]
        onAccepted: {
            var path = selectedFile.toString()
            if (path.startsWith("file://"))
                path = path.substring(7)
            App.loadAnimationPreview(path)
        }
    }

    ColumnLayout {
        width: Math.max(keyboardRoot.width - Kirigami.Units.gridUnit * 6, 200)
        spacing: Kirigami.Units.largeSpacing

    Label {
        text: App.keyboard.connected ? qsTr("Keyboard: connected")
             : qsTr("Keyboard: not connected (use Devices tab).")
        font.bold: true
    }
    RowLayout {
        Button {
            text: qsTr("Disconnect keyboard")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Release USB on this thread; device stays physically plugged in.")
            enabled: App.keyboard.connected
            onClicked: App.keyboard.disconnectDevice()
        }
        CheckBox {
            text: qsTr("USB debug")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Reconnect required: enables verbose USB when opening the keyboard.")
            checked: App.keyboard.debugUsb
            onToggled: function (c) { App.keyboard.debugUsb = c }
        }
    }
    Kirigami.Heading {
        level: 2
        text: qsTr("Inspect")
        Layout.fillWidth: true
    }
    Kirigami.Separator { Layout.fillWidth: true }
    RowLayout {
        Layout.fillWidth: true
        Button {
            text: qsTr("Refresh")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Read firmware version, brightness, and power state.")
            onClicked: App.keyboard.refreshInspect()
        }
        Label { text: qsTr("FW: %1").arg(App.keyboard.fwVersion) }
        Label { text: qsTr("Brightness: %1").arg(App.keyboard.brightnessRead) }
        Label { text: App.keyboard.isOff ? qsTr("State: off") : qsTr("State: on") }
    }
    SliderSpinRow {
        label: qsTr("Brightness 0–50")
        from: 0
        to: 50
        value: 25
        id: kbBrightRow
        Layout.fillWidth: true
    }
    Button {
        text: qsTr("Apply brightness")
        ToolTip.visible: hovered
        ToolTip.text: qsTr("Keyboard backlight 0–50 (device limit).")
        onClicked: App.keyboard.setBrightness(kbBrightRow.value)
    }
    Button {
        text: qsTr("Power off keyboard")
        ToolTip.visible: hovered
        ToolTip.text: qsTr("Same as CLI: keyboard power off")
        onClicked: App.keyboard.powerOff()
    }

    Kirigami.Heading {
        level: 2
        text: qsTr("Firmware effect")
        Layout.fillWidth: true
    }
    Kirigami.Separator { Layout.fillWidth: true }
    Label { text: qsTr("Choose effect (tap a chip)") }
    GridView {
        id: effGrid
        objectName: "keyboardEffectGrid"
        Layout.fillWidth: true
        height: Math.ceil(App.keyboardEffectNames.length / 3) * (Kirigami.Units.gridUnit * 5 + Kirigami.Units.smallSpacing)
            + Kirigami.Units.smallSpacing
        clip: false
        cellWidth: Math.max(width / 3, Kirigami.Units.gridUnit * 10)
        cellHeight: Kirigami.Units.gridUnit * 5 + Kirigami.Units.smallSpacing
        model: App.keyboardEffectNames
        delegate: EffectCard {
            width: effGrid.cellWidth - 6
            height: effGrid.cellHeight - 6
            required property int index
            effectName: App.keyboardEffectNames[index]
            selected: appShell.selectedKeyboardEffect === effectName
            onActivated: appShell.selectedKeyboardEffect = effectName
        }
    }
    KLayouts.FormLayout {
        Layout.fillWidth: true
        wideMode: true
        SliderSpinRow {
            id: effSpeedRow
            showLabel: false
            Kirigami.FormData.label: qsTr("Speed (0–10):")
            from: 0
            to: 10
            value: 5
            sliderMinimumWidth: 120
        }
        SliderSpinRow {
            id: effBrRow
            showLabel: false
            Kirigami.FormData.label: qsTr("Brightness (0–50):")
            from: 0
            to: 50
            value: 25
            sliderMinimumWidth: 120
        }
        ComboBox {
            id: effColor
            Kirigami.FormData.label: qsTr("Palette slot colour:")
            model: App.paletteSlotColorNames
            Layout.fillWidth: true
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Which palette colour slot the effect uses (where supported).")
        }
        ComboBox {
            id: effDir
            Kirigami.FormData.label: qsTr("Direction:")
            model: App.directionNames
            Layout.fillWidth: true
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Wave / marquee direction (effects that support it).")
        }
        CheckBox {
            id: effReactive
            Kirigami.FormData.label: qsTr("Options:")
            text: qsTr("Reactive")
        }
        CheckBox {
            id: effSave
            text: qsTr("Save to firmware")
        }
        Button {
            text: qsTr("Apply effect")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Send the selected firmware effect with the options above.")
            onClicked: App.keyboard.applyEffect(
                          appShell.selectedKeyboardEffect,
                          effSpeedRow.value, effBrRow.value,
                          effColor.currentText,
                          effDir.currentText,
                          effReactive.checked, effSave.checked)
        }
    }

    Kirigami.Heading {
        level: 2
        text: qsTr("Solid color")
        Layout.fillWidth: true
    }
    Kirigami.Separator { Layout.fillWidth: true }
    KLayouts.FormLayout {
        Layout.fillWidth: true
        wideMode: true
        RowLayout {
            Kirigami.FormData.label: qsTr("Named:")
            spacing: Kirigami.Units.smallSpacing
            ComboBox {
                id: solidCombo
                model: App.solidColorNames
                Layout.preferredWidth: 140
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Named colours from the CLI colour table.")
            }
            Button {
                text: qsTr("Apply named")
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Apply solid colour across the keyboard.")
                onClicked: App.keyboard.setSolidNamed(solidCombo.currentText)
            }
        }
        RowLayout {
            Kirigami.FormData.label: qsTr("RGB:")
            spacing: Kirigami.Units.smallSpacing
            ColorWell {
                toolTipText: qsTr("Open color picker (updates RGB spin boxes)")
                fillColor: Qt.rgba(sr.value / 255, sg.value / 255, sb.value / 255, 1)
                onClicked: kbSolidColorDialog.open()
            }
            SpinBox { id: sr; from: 0; to: 255; value: 255 }
            SpinBox { id: sg; from: 0; to: 255; value: 0 }
            SpinBox { id: sb; from: 0; to: 255; value: 0 }
            Button { text: qsTr("Apply RGB"); onClicked: App.keyboard.setSolidRgb(sr.value, sg.value, sb.value) }
        }
    }

    Kirigami.Heading {
        level: 2
        text: qsTr("Palette slots 1–7")
        Layout.fillWidth: true
    }
    Kirigami.Separator { Layout.fillWidth: true }
    KLayouts.FormLayout {
        Layout.fillWidth: true
        wideMode: true
        RowLayout {
            Kirigami.FormData.label: qsTr("Slot + RGB:")
            spacing: Kirigami.Units.smallSpacing
            SpinBox { id: palSlot; from: 1; to: 7; value: 1 }
            SpinBox { id: pr; from: 0; to: 255; value: 255 }
            SpinBox { id: pg; from: 0; to: 255; value: 0 }
            SpinBox { id: pb; from: 0; to: 255; value: 0 }
            ColorWell {
                fillColor: Qt.rgba(pr.value / 255, pg.value / 255, pb.value / 255, 1)
                toolTipText: qsTr("Click to open colour picker for this slot.")
                onClicked: kbPaletteColorDialog.open()
            }
            Button {
                text: qsTr("Set slot")
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Write RGB to palette slot 1–7.")
                onClicked: App.keyboard.setPaletteSlotRgb(palSlot.value, pr.value, pg.value, pb.value)
            }
        }
        RowLayout {
            Kirigami.FormData.label: qsTr("Actions:")
            spacing: Kirigami.Units.smallSpacing
            Button {
                text: qsTr("Restore default")
                onClicked: App.keyboard.paletteRestore()
            }
            Button {
                text: qsTr("Random palette")
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Random colour per slot (1–7).")
                onClicked: App.keyboard.paletteRandom()
            }
        }
    }

    RowLayout {
        Button {
            text: qsTr("Demo test pattern")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Run the firmware test pattern sequence.")
            onClicked: App.keyboard.demoTestPattern()
        }
        Button {
            text: qsTr("Freeze animation")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Match CLI: keyboard freeze-animation")
            onClicked: App.keyboard.freezeAnimation()
        }
    }

    Kirigami.Heading {
        level: 2
        text: qsTr("Animation file (DSL)")
        Layout.fillWidth: true
    }
    Kirigami.Separator { Layout.fillWidth: true }
    Label {
        text: App.animationFilePath.length > 0
              ? qsTr("File: %1").arg(App.animationFilePath)
              : qsTr("No file selected.")
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
    RowLayout {
        Layout.fillWidth: true
        SpinBox { id: animLoops; from: 1; to: 999; value: 1 }
        CheckBox { id: animForever; text: qsTr("Loop forever") }
        Button {
            text: qsTr("Pick file…")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Load a DSL script; preview appears below.")
            onClicked: kbAnimDialog.open()
        }
        Button {
            text: qsTr("Play")
            enabled: App.animationFilePath.length > 0 && App.keyboard.connected
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Run the loaded file on the USB worker thread.")
            onClicked: App.keyboard.playAnimationFile(App.animationFilePath, animLoops.value, animForever.checked)
        }
        Button {
            text: qsTr("Stop follow / animation")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Signal the background loop to stop.")
            onClicked: App.keyboard.stopFollowOrAnimation()
        }
    }
    Frame {
        Layout.fillWidth: true
        Layout.preferredHeight: 160
        padding: 4
        TextArea {
            anchors.fill: parent
            readOnly: true
            wrapMode: TextArea.Wrap
            text: App.animationPreviewText
            font.family: "monospace"
            selectByMouse: true
        }
    }

    Kirigami.Heading {
        level: 2
        text: qsTr("Follow screen (X11)")
        visible: App.keyboard.followScreenExtraOk
        Layout.fillWidth: true
    }
    Kirigami.Separator {
        Layout.fillWidth: true
        visible: App.keyboard.followScreenExtraOk
    }
    ColumnLayout {
        visible: App.keyboard.followScreenExtraOk
        Layout.fillWidth: true
        CheckBox { id: folFull; text: qsTr("Fullscreen"); checked: true }
        RowLayout {
            Label { text: qsTr("Region X Y W H") }
            SpinBox { id: fx; from: 0; to: 10000; value: 0 }
            SpinBox { id: fy; from: 0; to: 10000; value: 0 }
            SpinBox { id: fw; from: 1; to: 10000; value: 800 }
            SpinBox { id: fh; from: 1; to: 10000; value: 600 }
        }
        RowLayout {
            Button {
                text: qsTr("Start follow")
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Sample screen colours to keyboard (X11; needs [screen] extra).")
                onClicked: App.keyboard.startFollowScreen(folFull.checked, fx.value, fy.value, fw.value, fh.value)
            }
            Button {
                text: qsTr("Stop")
                onClicked: App.keyboard.stopFollowOrAnimation()
            }
        }
    }
    Label {
        visible: !App.keyboard.followScreenExtraOk
        text: qsTr("Follow screen needs: uv sync --extra screen")
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    Kirigami.Heading {
        level: 2
        text: qsTr("Per-key grid (click cell → color; Apply all)")
        Layout.fillWidth: true
    }
    Kirigami.Separator { Layout.fillWidth: true }
    KeyColorGrid {
        keyboard: App.keyboard
        Layout.fillWidth: true
        onCellClicked: function (row, col) {
            gridPick.row = row
            gridPick.col = col
            kbGridColorDialog.open()
        }
    }
    RowLayout {
        Layout.fillWidth: true
        Button {
            text: qsTr("Apply grid to keyboard")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Uploads the 6×21 colors to the keyboard (user mode).")
            onClicked: App.keyboard.applyKeyGrid(true)
        }
        Button { text: qsTr("Clear grid"); onClicked: App.keyboard.clearKeyGrid() }
    }
    }
}
