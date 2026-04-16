import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kirigami.layouts as KLayouts
import QtQuick.Dialogs
import components

/**
 * Keyboard device UI: primary/secondary headers, scroll body by subNavIndex, fixed footer.
 * subNavIndex is driven by the shell middle column (0–5).
 */
Item {
    id: keyboardRoot
    objectName: "keyboardPage"
    property var appShell
    /** Bound from main.qml middle nav */
    property int subNavIndex: 0

    /** Solid apply: named vs RGB (manual RGB clears named). */
    property bool solidPreferNamed: true
    property string solidPickName: ""

    property int paletteMirrorTick: 0

    QtObject {
        id: gridPick
        property int row: -1
        property int col: -1
    }

    Connections {
        target: App.keyboard
        function onPaletteMirrorChanged() {
            keyboardRoot.paletteMirrorTick++
        }
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
            keyboardRoot.solidPreferNamed = false
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

    function applyKeyboardConfiguration() {
        var m = keyboardRoot.subNavIndex
        if (m === 0) {
            App.keyboard.applyEffect(
                appShell.selectedKeyboardEffect,
                effSpeedRow.value,
                kbGlobalBright.value,
                effColor.currentText,
                effDir.currentText,
                effReactive.checked,
                effSave.checked
            )
        } else if (m === 1) {
            if (keyboardRoot.solidPreferNamed && keyboardRoot.solidPickName.length > 0)
                App.keyboard.setSolidNamed(keyboardRoot.solidPickName)
            else
                App.keyboard.setSolidRgb(sr.value, sg.value, sb.value)
        } else if (m === 2) {
            App.keyboard.setPaletteSlotRgb(palSlot.value, pr.value, pg.value, pb.value)
        } else if (m === 3) {
            App.keyboard.applyKeyGrid(true)
        }
    }

    function selectPaletteSlot(slot) {
        palSlot.value = slot
        var r = App.keyboard.paletteSlotR(slot)
        if (r >= 0) {
            pr.value = r
            pg.value = App.keyboard.paletteSlotG(slot)
            pb.value = App.keyboard.paletteSlotB(slot)
        }
    }

    function kbInfoSummary() {
        if (!App.keyboard.connected)
            return qsTr("Not connected. Turn on the sidebar switch or choose a device on Devices.")
        return qsTr("FW: %1 · Brightness: %2 · %3")
            .arg(App.keyboard.fwVersion)
            .arg(App.keyboard.brightnessRead)
            .arg(App.keyboard.isOff ? qsTr("Off") : qsTr("On"))
    }

    Component.onCompleted: {
        if (keyboardRoot.solidPickName.length === 0 && App.solidColorNames.length > 0)
            keyboardRoot.solidPickName = App.solidColorNames[0]
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
                        text: qsTr("Keyboard")
                    }
                    ToolButton {
                        icon.name: "dialog-information-symbolic"
                        ToolTip.text: qsTr("Device status")
                        onClicked: kbInfoPopup.open()
                    }
                    Popup {
                        id: kbInfoPopup
                        width: Math.min(keyboardRoot.width - Kirigami.Units.gridUnit * 4, 420)
                        padding: Kirigami.Units.mediumSpacing
                        modal: true
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                        contentItem: ColumnLayout {
                            spacing: Kirigami.Units.smallSpacing
                            width: kbInfoPopup.availableWidth
                            Label {
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                text: kbInfoSummary()
                            }
                            RowLayout {
                                spacing: Kirigami.Units.smallSpacing
                                Button {
                                    text: qsTr("Refresh")
                                    onClicked: App.keyboard.refreshInspect()
                                }
                                Button {
                                    text: qsTr("Disconnect")
                                    enabled: App.keyboard.connected
                                    onClicked: App.keyboard.disconnectDevice()
                                }
                            }
                        }
                    }
                    Item {
                        Layout.fillWidth: true
                    }
                    Label {
                        text: qsTr("Connected")
                        visible: App.keyboard.connected
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    SliderSpinRow {
                        id: kbGlobalBright
                        label: qsTr("Brightness 0–50")
                        from: 0
                        to: 50
                        value: 25
                        Layout.fillWidth: true
                        sliderMinimumWidth: 100
                    }
                    Button {
                        text: qsTr("Set brightness")
                        ToolTip.visible: hovered
                        ToolTip.text: qsTr("Device-wide level without changing the active effect.")
                        enabled: App.keyboard.connected
                        onClicked: App.keyboard.setBrightness(kbGlobalBright.value)
                    }
                    Label {
                        text: qsTr("Effect:")
                    }
                    ComboBox {
                        id: kbHeaderEffectCombo
                        model: App.keyboardEffectNames
                        Layout.preferredWidth: 180
                        Component.onCompleted: syncFromShell()
                        onModelChanged: syncFromShell()
                        function syncFromShell() {
                            var names = App.keyboardEffectNames
                            var sel = appShell.selectedKeyboardEffect
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
                            appShell.selectedKeyboardEffect = textAt(ix)
                        }
                        ToolTip.visible: hovered
                        ToolTip.text: qsTr("Selected firmware effect (used when applying in Firmware mode).")
                    }

                    Connections {
                        target: appShell
                        function onSelectedKeyboardEffectChanged() {
                            kbHeaderEffectCombo.syncFromShell()
                        }
                    }
                }
            }

        Kirigami.Separator {
            Layout.fillWidth: true
        }

        ScrollView {
            id: kbScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            StackLayout {
                id: kbModeStack
                width: Math.max(kbScroll.availableWidth, 200)
                currentIndex: keyboardRoot.subNavIndex
                implicitHeight: {
                    var it = kbModeStack.itemAt(kbModeStack.currentIndex)
                    return it ? it.implicitHeight : Kirigami.Units.gridUnit * 20
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    width: parent.width
                    Label {
                        text: qsTr("Choose effect (tap a chip)")
                        Layout.leftMargin: Kirigami.Units.smallSpacing
                    }
                    GridView {
                        id: effGrid
                        objectName: "keyboardEffectGrid"
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.ceil(App.keyboardEffectNames.length / 3) * (Kirigami.Units.gridUnit * 5 + Kirigami.Units.smallSpacing)
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
                        Layout.leftMargin: Kirigami.Units.smallSpacing
                        Layout.rightMargin: Kirigami.Units.smallSpacing
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
                    }
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    width: parent.width
                    Layout.leftMargin: Kirigami.Units.smallSpacing
                    Layout.rightMargin: Kirigami.Units.smallSpacing
                    Label {
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        text: qsTr("Named swatches and RGB are both shown. Apply sends the named colour if you last picked a swatch; editing RGB switches to custom RGB.")
                        font.italic: true
                    }
                    Label {
                        text: qsTr("Named colours")
                    }
                    Flow {
                        id: solidFlow
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing
                        Repeater {
                            model: App.solidColorEntries
                            delegate: Rectangle {
                                required property var modelData
                                width: (solidFlow.width - solidFlow.spacing * 3) / 4
                                height: Kirigami.Units.gridUnit * 5
                                radius: 4
                                border.width: keyboardRoot.solidPreferNamed && keyboardRoot.solidPickName === modelData.name ? 3 : 1
                                border.color: keyboardRoot.solidPreferNamed && keyboardRoot.solidPickName === modelData.name
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
                                        keyboardRoot.solidPreferNamed = true
                                        keyboardRoot.solidPickName = modelData.name
                                        sr.value = modelData.r
                                        sg.value = modelData.g
                                        sb.value = modelData.b
                                    }
                                }
                            }
                        }
                    }
                    Label {
                        text: qsTr("RGB")
                    }
                    RowLayout {
                        spacing: Kirigami.Units.smallSpacing
                        ColorWell {
                            toolTipText: qsTr("Open color picker (updates RGB spin boxes)")
                            fillColor: Qt.rgba(sr.value / 255, sg.value / 255, sb.value / 255, 1)
                            onClicked: kbSolidColorDialog.open()
                        }
                        SpinBox {
                            id: sr
                            property bool _muteSolid: true
                            Component.onCompleted: _muteSolid = false
                            from: 0
                            to: 255
                            value: 255
                            onValueChanged: {
                                if (!_muteSolid)
                                    keyboardRoot.solidPreferNamed = false
                            }
                        }
                        SpinBox {
                            id: sg
                            property bool _muteSolid: true
                            Component.onCompleted: _muteSolid = false
                            from: 0
                            to: 255
                            value: 0
                            onValueChanged: {
                                if (!_muteSolid)
                                    keyboardRoot.solidPreferNamed = false
                            }
                        }
                        SpinBox {
                            id: sb
                            property bool _muteSolid: true
                            Component.onCompleted: _muteSolid = false
                            from: 0
                            to: 255
                            value: 0
                            onValueChanged: {
                                if (!_muteSolid)
                                    keyboardRoot.solidPreferNamed = false
                            }
                        }
                    }
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    width: parent.width
                    Layout.leftMargin: Kirigami.Units.smallSpacing
                    Layout.rightMargin: Kirigami.Units.smallSpacing
                    Label {
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        text: qsTr("Palette colours cannot be read from the device; swatches show session state after writes, restore, or randomize.")
                        font.italic: true
                    }
                    Label {
                        text: qsTr("Slots 1–7 (tap to select)")
                    }
                    RowLayout {
                        spacing: Kirigami.Units.smallSpacing
                        Repeater {
                            model: [1, 2, 3, 4, 5, 6, 7]
                            delegate: Rectangle {
                                required property int modelData
                                width: Kirigami.Units.gridUnit * 5
                                height: Kirigami.Units.gridUnit * 5
                                radius: 4
                                property int slotNum: modelData
                                border.width: palSlot.value === slotNum ? 3 : 1
                                border.color: palSlot.value === slotNum
                                              ? Kirigami.Theme.highlightColor
                                              : Qt.alpha(Kirigami.Theme.disabledTextColor, 0.22)
                                color: {
                                    keyboardRoot.paletteMirrorTick
                                    var r = App.keyboard.paletteSlotR(slotNum)
                                    if (r < 0)
                                        return Kirigami.Theme.disabledTextColor
                                    return Qt.rgba(App.keyboard.paletteSlotR(slotNum) / 255,
                                                   App.keyboard.paletteSlotG(slotNum) / 255,
                                                   App.keyboard.paletteSlotB(slotNum) / 255, 1)
                                }
                                Label {
                                    anchors.centerIn: parent
                                    text: slotNum
                                    color: Kirigami.Theme.textColor
                                }
                                ToolTip.visible: ma.containsMouse
                                ToolTip.text: App.keyboard.paletteSlotKnown(slotNum)
                                                 ? qsTr("Slot %1").arg(slotNum)
                                                 : qsTr("Slot %1 — not synced this session yet").arg(slotNum)
                                MouseArea {
                                    id: ma
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onClicked: keyboardRoot.selectPaletteSlot(slotNum)
                                }
                            }
                        }
                    }
                    KLayouts.FormLayout {
                        Layout.fillWidth: true
                        wideMode: true
                        RowLayout {
                            Kirigami.FormData.label: qsTr("Slot + RGB:")
                            spacing: Kirigami.Units.smallSpacing
                            SpinBox {
                                id: palSlot
                                from: 1
                                to: 7
                                value: 1
                            }
                            SpinBox {
                                id: pr
                                from: 0
                                to: 255
                                value: 255
                            }
                            SpinBox {
                                id: pg
                                from: 0
                                to: 255
                                value: 0
                            }
                            SpinBox {
                                id: pb
                                from: 0
                                to: 255
                                value: 0
                            }
                            ColorWell {
                                fillColor: Qt.rgba(pr.value / 255, pg.value / 255, pb.value / 255, 1)
                                toolTipText: qsTr("Click to open colour picker for this slot.")
                                onClicked: kbPaletteColorDialog.open()
                            }
                        }
                        RowLayout {
                            Kirigami.FormData.label: qsTr("Auxiliary:")
                            spacing: Kirigami.Units.smallSpacing
                            Button {
                                text: qsTr("Restore default palette")
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
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    width: parent.width
                    Layout.leftMargin: Kirigami.Units.smallSpacing
                    Layout.rightMargin: Kirigami.Units.smallSpacing
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
                        Button {
                            text: qsTr("Clear grid")
                            onClicked: App.keyboard.clearKeyGrid()
                        }
                    }
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    width: parent.width
                    Layout.leftMargin: Kirigami.Units.smallSpacing
                    Layout.rightMargin: Kirigami.Units.smallSpacing
                    Label {
                        text: qsTr("These actions are independent of Apply below.")
                        font.italic: true
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    Kirigami.Heading {
                        level: 4
                        text: qsTr("Animation file (DSL)")
                    }
                    Label {
                        text: App.animationFilePath.length > 0
                              ? qsTr("File: %1").arg(App.animationFilePath)
                              : qsTr("No file selected.")
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        SpinBox {
                            id: animLoops
                            from: 1
                            to: 999
                            value: 1
                        }
                        CheckBox {
                            id: animForever
                            text: qsTr("Loop forever")
                        }
                        Button {
                            text: qsTr("Pick file…")
                            onClicked: kbAnimDialog.open()
                        }
                        Button {
                            text: qsTr("Play")
                            enabled: App.animationFilePath.length > 0 && App.keyboard.connected
                            onClicked: App.keyboard.playAnimationFile(App.animationFilePath, animLoops.value, animForever.checked)
                        }
                        Button {
                            text: qsTr("Stop follow / animation")
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
                        level: 4
                        text: qsTr("Follow screen (X11)")
                        visible: App.keyboard.followScreenExtraOk
                    }
                    ColumnLayout {
                        visible: App.keyboard.followScreenExtraOk
                        Layout.fillWidth: true
                        CheckBox {
                            id: folFull
                            text: qsTr("Fullscreen")
                            checked: true
                        }
                        RowLayout {
                            Label {
                                text: qsTr("Region X Y W H")
                            }
                            SpinBox {
                                id: fx
                                from: 0
                                to: 10000
                                value: 0
                            }
                            SpinBox {
                                id: fy
                                from: 0
                                to: 10000
                                value: 0
                            }
                            SpinBox {
                                id: fw
                                from: 1
                                to: 10000
                                value: 800
                            }
                            SpinBox {
                                id: fh
                                from: 1
                                to: 10000
                                value: 600
                            }
                        }
                        RowLayout {
                            Button {
                                text: qsTr("Start follow")
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
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    width: parent.width
                    Layout.leftMargin: Kirigami.Units.smallSpacing
                    Layout.rightMargin: Kirigami.Units.smallSpacing
                    RowLayout {
                        Button {
                            text: qsTr("Demo test pattern")
                            onClicked: App.keyboard.demoTestPattern()
                        }
                        Button {
                            text: qsTr("Freeze animation")
                            onClicked: App.keyboard.freezeAnimation()
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
                ToolTip.text: qsTr("Turn keyboard backlight off. Current effect is saved for Power on.")
                enabled: App.keyboard.connected
                onClicked: App.keyboard.powerOff()
            }
            Button {
                text: qsTr("Power on")
                ToolTip.visible: hovered
                ToolTip.text: App.keyboard.replayPowerOnAvailable
                              ? qsTr("Restore the backlight state from before Power off.")
                              : qsTr("Use after Power off once a snapshot exists.")
                enabled: App.keyboard.connected && App.keyboard.replayPowerOnAvailable
                onClicked: App.keyboard.powerOnReplay()
            }
            Item {
                Layout.fillWidth: true
            }
            Button {
                id: keyboardApplyConfigButton
                objectName: "keyboardApplyConfig"
                text: qsTr("Apply")
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Apply the current mode (Firmware, Solid, Palette, or Per-key).")
                enabled: App.keyboard.connected && keyboardRoot.subNavIndex >= 0 && keyboardRoot.subNavIndex <= 3
                onClicked: keyboardRoot.applyKeyboardConfiguration()
            }
        }
        }
    }
}
