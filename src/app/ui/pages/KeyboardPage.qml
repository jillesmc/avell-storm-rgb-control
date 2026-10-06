import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import QtQuick.Dialogs
import components

/**
 * Keyboard device UI: primary/secondary headers, scroll body by subNavIndex, fixed footer.
 * subNavIndex is driven by the shell middle column (0–7):
 * 0 Firmware, 1 Palette, 2 Solid, 3 Per-key, 4 Animation file, 5 Follow screen, 6 Calibration, 7 Tools.
 */
Item {
    id: keyboardRoot
    objectName: "keyboardPage"
    property var appShell
    /** Bound from main.qml middle nav */
    property int subNavIndex: 0

    readonly property int pageFirmware: 0
    readonly property int pagePalette: 1
    readonly property int pageSolid: 2
    readonly property int pagePerKey: 3
    readonly property int pageAnimation: 4
    readonly property int pageFollow: 5
    readonly property int pageCalibration: 6
    readonly property int pageTools: 7
    /** Match palette slot swatch size (gridUnit * 5). */
    readonly property int solidSwatchCell: Kirigami.Units.gridUnit * 5
    readonly property bool showDeviceBrightnessBlock: keyboardRoot.subNavIndex !== keyboardRoot.pagePalette
        && keyboardRoot.subNavIndex !== keyboardRoot.pageTools

    /** Solid apply: named vs RGB (manual RGB clears named). */
    property bool solidPreferNamed: true
    property string solidPickName: ""

    property int paletteMirrorTick: 0
    property var selectedPerKeyIds: []
    property string activePerKeyId: ""
    property color lastPerKeyColor: Qt.rgba(0.21, 0.21, 0.21, 1)
    /** Closed-state label for firmware colour combo (updated only on index / palette change). */
    property string effColorSummaryText: ""

    /** True after the user changes a firmware control; cleared after a debounced apply. */
    property bool firmwareEffectDirty: false
    /** Suppress one-shot apply when wiring initial combo indices before user interaction. */
    property bool firmwareApplySuppressed: true

    /** Opt-in via env ``AVELL_DEBUG_FIRMWARE_UI`` (see ``App.debugFirmwareUi``). */
    readonly property bool fwDiag: App.debugFirmwareUi
    property int _fwDiagReqN: 0
    property int _fwDiagPushN: 0
    property int _fwDiagScrollBodyWidthTicks: 0
    property int _fwDiagPaletteTicks: 0

    function fwDiagLog(msg) {
        if (!keyboardRoot.fwDiag)
            return
        console.log("[FirmwareUI]", msg)
    }

    function brightnessPercentToFw(percent) {
        return Math.max(0, Math.min(50, Math.round(percent * 50 / 100)))
    }
    function brightnessFwToPercent(fw) {
        return Math.max(0, Math.min(100, Math.round(fw * 100 / 50)))
    }

    function firmwareColorKeyAt(index) {
        var rows = App.firmwarePaletteColorChoices
        if (!rows || index < 0 || index >= rows.length)
            return "random"
        return rows[index].key
    }

    function firmwareColorTitleRow(md) {
        if (!md)
            return ""
        if (md.palette_slot >= 1 && md.palette_slot <= 7)
            return qsTr("Slot %1").arg(md.palette_slot)
        if (md.key === "random")
            return qsTr("Random")
        return qsTr("None")
    }

    function _byteHex(v) {
        var s = Math.round(v).toString(16)
        return s.length === 1 ? "0" + s : s
    }

    function setLastPerKeyColorFromQmlColor(c) {
        lastPerKeyColor = Qt.rgba(c.r, c.g, c.b, 1)
    }

    function firmwareColorHexRow(md) {
        var tick = keyboardRoot.paletteMirrorTick
        void tick
        if (!md || md.palette_slot < 1 || md.palette_slot > 7)
            return "—"
        var r = App.keyboard.paletteSlotR(md.palette_slot)
        if (r < 0)
            return "—"
        return "#" + _byteHex(r) + _byteHex(App.keyboard.paletteSlotG(md.palette_slot))
            + _byteHex(App.keyboard.paletteSlotB(md.palette_slot))
    }

    function firmwareColorSwatch(md) {
        var tick = keyboardRoot.paletteMirrorTick
        void tick
        if (!md || md.palette_slot < 1 || md.palette_slot > 7) {
            if (md && md.key === "random")
                return Kirigami.Theme.highlightColor
            return Kirigami.ColorUtils.linearInterpolation(
                Kirigami.Theme.backgroundColor,
                Kirigami.Theme.textColor,
                0.15)
        }
        var r = App.keyboard.paletteSlotR(md.palette_slot)
        if (r < 0)
            return Kirigami.Theme.backgroundColor
        return Qt.rgba(r / 255, App.keyboard.paletteSlotG(md.palette_slot) / 255,
                       App.keyboard.paletteSlotB(md.palette_slot) / 255, 1)
    }

    function firmwareColorComboDisplay(index) {
        var rows = App.firmwarePaletteColorChoices
        var tick = keyboardRoot.paletteMirrorTick
        void tick
        if (!rows || index < 0 || index >= rows.length)
            return ""
        var md = rows[index]
        if (md.palette_slot >= 1 && md.palette_slot <= 7)
            return firmwareColorTitleRow(md) + " · " + firmwareColorHexRow(md)
        return firmwareColorTitleRow(md)
    }

    function syncFirmwareColorSummaryText() {
        keyboardRoot.effColorSummaryText = keyboardRoot.firmwareColorComboDisplay(effColor.currentIndex)
    }

    Timer {
        id: fwEffectApplyTimer
        interval: 200
        repeat: false
        onTriggered: {
            if (keyboardRoot.fwDiag) {
                keyboardRoot.fwDiagLog("fwEffectApplyTimer fired dirty=" + keyboardRoot.firmwareEffectDirty
                    + " subNav=" + keyboardRoot.subNavIndex + " connected=" + App.keyboard.connected)
            }
            if (!keyboardRoot.firmwareEffectDirty)
                return
            if (keyboardRoot.subNavIndex !== keyboardRoot.pageFirmware || !App.keyboard.connected) {
                keyboardRoot.firmwareEffectDirty = false
                return
            }
            keyboardRoot.pushFirmwareEffectToDevice()
            keyboardRoot.firmwareEffectDirty = false
        }
    }

    Timer {
        id: fwDiagSummaryTimer
        interval: 1000
        repeat: true
        running: keyboardRoot.fwDiag && keyboardRoot.subNavIndex === keyboardRoot.pageFirmware
        property int _r0: 0
        property int _p0: 0
        property int _w0: 0
        property int _pal0: 0
        onTriggered: {
            if (!keyboardRoot.fwDiag)
                return
            var r = keyboardRoot._fwDiagReqN
            var p = keyboardRoot._fwDiagPushN
            var w = keyboardRoot._fwDiagScrollBodyWidthTicks
            var pal = keyboardRoot._fwDiagPaletteTicks
            console.log("[FirmwareUI/summary 1s] req+" + (r - _r0) + " push+" + (p - _p0)
                + " scrollBodyWidth+" + (w - _w0) + " paletteMirror+" + (pal - _pal0)
                + " pageW=" + keyboardRoot.width + " scrollBodyW=" + kbScrollBody.width
                + " kbAvailW=" + kbScroll.availableWidth + " connected=" + App.keyboard.connected)
            _r0 = r
            _p0 = p
            _w0 = w
            _pal0 = pal
        }
    }

    property bool solidApplyPending: false
    Timer {
        id: solidApplyTimer
        interval: 200
        repeat: false
        onTriggered: {
            if (!keyboardRoot.solidApplyPending)
                return
            if (keyboardRoot.subNavIndex !== keyboardRoot.pageSolid || !App.keyboard.connected) {
                keyboardRoot.solidApplyPending = false
                return
            }
            keyboardRoot.pushSolidToDevice()
            keyboardRoot.solidApplyPending = false
        }
    }

    function requestSolidApply() {
        if (keyboardRoot.subNavIndex !== keyboardRoot.pageSolid || !App.keyboard.connected)
            return
        keyboardRoot.solidApplyPending = true
        solidApplyTimer.restart()
    }

    function pushSolidToDevice() {
        if (keyboardRoot.solidPreferNamed && keyboardRoot.solidPickName.length > 0)
            App.keyboard.setSolidNamed(keyboardRoot.solidPickName)
        else
            App.keyboard.setSolidRgb(sr.value, sg.value, sb.value)
    }

    /** Call only from explicit user edits (chips, combos, speed, checkboxes). */
    function requestFirmwareEffectApply() {
        if (keyboardRoot.firmwareApplySuppressed)
            return
        if (keyboardRoot.subNavIndex !== keyboardRoot.pageFirmware || !App.keyboard.connected)
            return
        keyboardRoot.firmwareEffectDirty = true
        if (keyboardRoot.fwDiag) {
            keyboardRoot._fwDiagReqN++
            keyboardRoot.fwDiagLog("requestFirmwareEffectApply #" + keyboardRoot._fwDiagReqN)
        }
        fwEffectApplyTimer.restart()
    }

    function pushFirmwareEffectToDevice() {
        if (keyboardRoot.subNavIndex !== keyboardRoot.pageFirmware || !App.keyboard.connected)
            return
        if (keyboardRoot.fwDiag) {
            keyboardRoot._fwDiagPushN++
            keyboardRoot.fwDiagLog("pushFirmwareEffectToDevice #" + keyboardRoot._fwDiagPushN
                + " effect=" + appShell.selectedKeyboardEffect)
        }
        var bFw = keyboardRoot.brightnessPercentToFw(kbDeviceBright.value)
        App.keyboard.applyEffect(
            appShell.selectedKeyboardEffect,
            effSpeedRow.value,
            bFw,
            keyboardRoot.firmwareColorKeyAt(effColor.currentIndex),
            effDir.currentText,
            effReactive.checked,
            effSave.checked
        )
    }

    QtObject {
        id: gridPick
        property string keyId: ""
    }

    Connections {
        target: App.keyboard
        function onPaletteMirrorChanged() {
            keyboardRoot.paletteMirrorTick++
            if (keyboardRoot.fwDiag)
                keyboardRoot._fwDiagPaletteTicks++
            keyboardRoot.syncFirmwareColorSummaryText()
        }
        function onConnectedChanged() {
            if (!App.keyboard.connected) {
                fwEffectApplyTimer.stop()
                solidApplyTimer.stop()
                keyboardRoot.firmwareEffectDirty = false
                keyboardRoot.solidApplyPending = false
            }
        }
    }

    ColorDialog {
        id: kbGridColorDialog
        title: qsTr("Key color")
        onAccepted: {
            if (gridPick.keyId.length > 0) {
                var c = kbGridColorDialog.selectedColor
                keyboardRoot.setLastPerKeyColorFromQmlColor(c)
                App.keyboard.setKeyById(gridPick.keyId,
                                        Math.round(c.r * 255),
                                        Math.round(c.g * 255),
                                        Math.round(c.b * 255), false)
            }
        }
    }

    ColorDialog {
        id: kbGridBatchColorDialog
        title: qsTr("Selection color")
        onAccepted: {
            if (keyboardRoot.selectedPerKeyIds.length === 0)
                return
            var c = kbGridBatchColorDialog.selectedColor
            keyboardRoot.setLastPerKeyColorFromQmlColor(c)
            App.keyboard.setKeysByIdColor(
                keyboardRoot.selectedPerKeyIds,
                Math.round(c.r * 255),
                Math.round(c.g * 255),
                Math.round(c.b * 255),
                false)
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
            keyboardRoot.requestSolidApply()
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
        if (m === keyboardRoot.pageFirmware) {
            keyboardRoot.pushFirmwareEffectToDevice()
        } else if (m === keyboardRoot.pagePalette) {
            App.keyboard.setPaletteSlotRgb(palSlot.value, pr.value, pg.value, pb.value)
        } else if (m === keyboardRoot.pageSolid) {
            keyboardRoot.pushSolidToDevice()
        } else if (m === keyboardRoot.pagePerKey) {
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
        return qsTr("FW: %1 · Brightness: %2% · %3")
            .arg(App.keyboard.fwVersion)
            .arg(keyboardRoot.brightnessFwToPercent(App.keyboard.brightnessRead))
            .arg(App.keyboard.isOff ? qsTr("Off") : qsTr("On"))
    }

    Component.onCompleted: {
        if (keyboardRoot.solidPickName.length === 0 && App.solidColorNames.length > 0)
            keyboardRoot.solidPickName = App.solidColorNames[0]
        Qt.callLater(function () {
            keyboardRoot.firmwareApplySuppressed = false
            keyboardRoot.syncFirmwareColorSummaryText()
        })
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

            }

        Kirigami.Separator {
            Layout.fillWidth: true
        }

        ScrollView {
            id: kbScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            padding: 0
            leftPadding: 0
            /**
             * Fixed right gutter for the vertical scrollbar. Toggling padding from contentHeight
             * near the threshold changes availableWidth and can reflow content → layout thrash / freeze.
             */
            readonly property int _kbScrollRightGutter: Math.max(
                Kirigami.Units.gridUnit,
                Math.ceil(kbVBar.implicitWidth + Kirigami.Units.smallSpacing))
            rightPadding: _kbScrollRightGutter
            topPadding: 0
            bottomPadding: 0

            ScrollBar.vertical: ScrollBar {
                id: kbVBar
                policy: ScrollBar.AsNeeded
                parent: kbScroll
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.right: parent.right
            }
            ScrollBar.horizontal: ScrollBar {
                policy: ScrollBar.AlwaysOff
                parent: kbScroll
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
            }

            /**
             * StackLayout.implicitWidth is the max of *all* stacked children, not the visible one.
             * Using that here widened every tab to the palette row minimum → empty band + narrow grid.
             * Keep scroll content locked to viewport width; reflow happens inside each page.
             */
            Item {
                id: kbScrollBody
                readonly property Item currentPage: kbModeStack.itemAt(kbModeStack.currentIndex)
                implicitHeight: kbOuterColumn.implicitHeight
                width: kbScroll.availableWidth
                height: Math.round(implicitHeight)
                onWidthChanged: {
                    if (keyboardRoot.fwDiag && keyboardRoot.subNavIndex === keyboardRoot.pageFirmware)
                        keyboardRoot._fwDiagScrollBodyWidthTicks++
                }

                ColumnLayout {
                    id: kbOuterColumn
                    width: parent.width
                    spacing: Kirigami.Units.mediumSpacing

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing
                        visible: keyboardRoot.showDeviceBrightnessBlock

                        Kirigami.Heading {
                            level: 4
                            text: qsTr("Device")
                        }
                        Label {
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            text: qsTr("Backlight level shown as 0–100% (device uses 0–50). Applies immediately; if a firmware effect is active, it is re-sent so the controller stays consistent.")
                            font.italic: true
                        }
                        SliderSpinRow {
                            id: kbDeviceBright
                            label: qsTr("Brightness (%)")
                            from: 0
                            to: 100
                            value: 50
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            sliderMinimumWidth: 72
                            enabled: App.keyboard.connected
                            onUserAdjusted: function (v) {
                                App.keyboard.requestBrightnessFromUi(keyboardRoot.brightnessPercentToFw(v))
                            }
                        }

                        Kirigami.Separator {
                            Layout.fillWidth: true
                        }
                    }

                    StackLayout {
                        id: kbModeStack
                        Layout.fillWidth: true
                        currentIndex: keyboardRoot.subNavIndex
                        implicitHeight: {
                            var it = kbModeStack.itemAt(kbModeStack.currentIndex)
                            return it ? it.implicitHeight : Kirigami.Units.gridUnit * 20
                        }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Layout.fillWidth: true
                    width: parent.width
                    Kirigami.Heading {
                        level: 4
                        text: qsTr("Firmware (controller)")
                    }
                    Label {
                        text: qsTr("Choose effect (tap a chip)")
                        Layout.leftMargin: Kirigami.Units.smallSpacing
                    }
                    Flow {
                        id: effGrid
                        objectName: "keyboardEffectGrid"
                        Layout.fillWidth: true
                        width: parent.width
                        spacing: Kirigami.Units.smallSpacing

                        Repeater {
                            model: App.keyboardEffectNames
                            delegate: EffectCard {
                                required property int index
                                effectName: App.keyboardEffectNames[index]
                                selected: appShell.selectedKeyboardEffect === effectName
                                onActivated: {
                                    appShell.selectedKeyboardEffect = effectName
                                    keyboardRoot.requestFirmwareEffectApply()
                                }
                            }
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                        spacing: Kirigami.Units.smallSpacing

                        Label {
                            text: qsTr("Cycle time (0–10):")
                            enabled: App.keyboard.effectSupports(appShell.selectedKeyboardEffect, "speed")
                        }
                        Label {
                            text: qsTr("Firmware timing index for one animation cycle (not seconds). Higher values often slow the effect; behaviour depends on the selected effect.")
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            font: Kirigami.Theme.smallFont
                            opacity: 0.82
                            enabled: App.keyboard.effectSupports(appShell.selectedKeyboardEffect, "speed")
                        }
                        SliderSpinRow {
                            id: effSpeedRow
                            showLabel: false
                            spinBeforeSlider: false
                            from: 0
                            to: 10
                            value: 5
                            sliderMinimumWidth: 120
                            Layout.fillWidth: true
                            Layout.maximumWidth: Kirigami.Units.gridUnit * 12
                            enabled: App.keyboard.effectSupports(appShell.selectedKeyboardEffect, "speed")
                            onUserAdjusted: keyboardRoot.requestFirmwareEffectApply()
                        }

                        Label {
                            text: qsTr("Palette slot colour:")
                            enabled: App.keyboard.effectSupports(appShell.selectedKeyboardEffect, "color")
                        }
                        ComboBox {
                            id: effColor
                            objectName: "keyboardFirmwareColorCombo"
                            model: App.firmwarePaletteColorChoices
                            textRole: "key"
                            valueRole: "key"
                            Layout.fillWidth: true
                            Layout.maximumWidth: Kirigami.Units.gridUnit * 22
                            enabled: App.keyboard.effectSupports(appShell.selectedKeyboardEffect, "color")
                            displayText: keyboardRoot.effColorSummaryText
                            delegate: ItemDelegate {
                                id: fwColorDel
                                required property int index
                                required property var modelData
                                contentItem: RowLayout {
                                    spacing: Kirigami.Units.smallSpacing
                                    Rectangle {
                                        width: Kirigami.Units.gridUnit
                                        height: Kirigami.Units.gridUnit
                                        radius: 2
                                        color: keyboardRoot.firmwareColorSwatch(fwColorDel.modelData)
                                        border.width: 1
                                        border.color: Qt.alpha(Kirigami.Theme.textColor, 0.22)
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 0
                                        Label {
                                            text: keyboardRoot.firmwareColorTitleRow(fwColorDel.modelData)
                                            font.weight: Font.Medium
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }
                                        Label {
                                            text: keyboardRoot.firmwareColorHexRow(fwColorDel.modelData)
                                            font: Kirigami.Theme.smallFont
                                            opacity: 0.85
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }
                                    }
                                }
                            }
                            ToolTip.visible: hovered
                            ToolTip.text: qsTr("Which palette slot the effect reads (1–7). Hex shows the mirrored session colour after writes or restore.")
                            onActivated: keyboardRoot.requestFirmwareEffectApply()
                            onCurrentIndexChanged: keyboardRoot.syncFirmwareColorSummaryText()
                            Component.onCompleted: {
                                currentIndex = 0
                                keyboardRoot.syncFirmwareColorSummaryText()
                            }
                        }

                        Label {
                            text: qsTr("Direction:")
                            enabled: App.keyboard.effectSupports(appShell.selectedKeyboardEffect, "direction")
                        }
                        ComboBox {
                            id: effDir
                            model: App.directionNames
                            Layout.fillWidth: true
                            Layout.maximumWidth: Kirigami.Units.gridUnit * 12
                            enabled: App.keyboard.effectSupports(appShell.selectedKeyboardEffect, "direction")
                            ToolTip.visible: hovered
                            ToolTip.text: qsTr("Wave direction (only effects that use direction, e.g. wave).")
                            onActivated: keyboardRoot.requestFirmwareEffectApply()
                        }

                        Label { text: qsTr("Options:") }
                        CheckBox {
                            id: effReactive
                            text: qsTr("Reactive")
                            enabled: App.keyboard.effectSupports(appShell.selectedKeyboardEffect, "reactive")
                            onClicked: keyboardRoot.requestFirmwareEffectApply()
                        }
                        CheckBox {
                            id: effSave
                            text: qsTr("Save to firmware")
                            enabled: App.keyboard.effectSupports(appShell.selectedKeyboardEffect, "save")
                            onClicked: keyboardRoot.requestFirmwareEffectApply()
                        }
                    }
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Layout.fillWidth: true
                    width: parent.width
                    Kirigami.Heading {
                        level: 4
                        text: qsTr("Device · palette slots (for firmware effects)")
                    }
                    Label {
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        text: qsTr("Palette colours cannot be read from the device; swatches show session state after writes, restore, or randomize.")
                        font.italic: true
                    }
                    Label {
                        text: qsTr("Slots 1–7 (tap to select)")
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing
                        Layout.minimumWidth: 0
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
                                                 : qsTr("Slot %1 — firmware default colours (nothing written this session yet)").arg(slotNum)
                                MouseArea {
                                    id: ma
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onClicked: keyboardRoot.selectPaletteSlot(slotNum)
                                }
                            }
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                        spacing: Kirigami.Units.smallSpacing

                        Label { text: qsTr("Slot + RGB:") }
                        Flow {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
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

                        Label { text: qsTr("Auxiliary:") }
                        Flow {
                            Layout.fillWidth: true
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
                    Layout.fillWidth: true
                    width: parent.width
                    Kirigami.Heading {
                        level: 4
                        text: qsTr("Software (user): solid colour")
                    }
                    Label {
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        text: qsTr("Named swatches and RGB are both shown. Changes apply automatically while you are on this tab; picking a swatch sends the named colour, and editing RGB switches to custom RGB.")
                        font.italic: true
                    }
                    Label {
                        text: qsTr("Named colours")
                    }
                    Flow {
                        id: solidFlow
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing
                        readonly property int cellW: keyboardRoot.solidSwatchCell
                        readonly property int columns: Math.max(1, Math.floor((width + spacing) / (cellW + spacing)))
                        Repeater {
                            model: App.solidColorEntries
                            delegate: Rectangle {
                                required property var modelData
                                width: solidFlow.cellW
                                height: solidFlow.cellW
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
                                        keyboardRoot.requestSolidApply()
                                    }
                                }
                            }
                        }
                    }
                    Label {
                        text: qsTr("RGB")
                    }
                    Flow {
                        Layout.fillWidth: true
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
                                if (!_muteSolid) {
                                    keyboardRoot.solidPreferNamed = false
                                    keyboardRoot.requestSolidApply()
                                }
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
                                if (!_muteSolid) {
                                    keyboardRoot.solidPreferNamed = false
                                    keyboardRoot.requestSolidApply()
                                }
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
                                if (!_muteSolid) {
                                    keyboardRoot.solidPreferNamed = false
                                    keyboardRoot.requestSolidApply()
                                }
                            }
                        }
                    }
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Layout.fillWidth: true
                    width: parent.width
                    Kirigami.Heading {
                        level: 4
                        text: qsTr("Software (user): keyboard layout")
                    }
                    Label {
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        text: qsTr("Pick real keys directly from the layout. Click to set one key; drag to select multiple keys and apply one color to all.")
                        font.italic: true
                    }
                    KeyboardLayoutView {
                        keyboard: App.keyboard
                        Layout.fillWidth: true
                        selectedKeyIds: keyboardRoot.selectedPerKeyIds
                        calibratedKeyIds: App.keyboard.calibratedKeyIds
                        conflictKeyIds: App.keyboard.conflictKeyIds
                        onKeyActivated: function (keyId) {
                            keyboardRoot.activePerKeyId = keyId
                            keyboardRoot.selectedPerKeyIds = [keyId]
                            gridPick.keyId = keyId
                            kbGridColorDialog.open()
                        }
                        onSelectionChanged: function (keyIds) {
                            keyboardRoot.selectedPerKeyIds = keyIds
                            keyboardRoot.activePerKeyId = keyIds.length > 0 ? String(keyIds[0]) : ""
                        }
                    }
                    RowLayout {
                        Label {
                            text: keyboardRoot.selectedPerKeyIds.length > 0
                                  ? qsTr("Selected: %1 key(s)").arg(keyboardRoot.selectedPerKeyIds.length)
                                  : qsTr("Selected: none")
                        }
                        Label {
                            visible: keyboardRoot.activePerKeyId.length > 0
                            text: qsTr("Active key: %1").arg(keyboardRoot.activePerKeyId)
                        }
                        Label {
                            visible: App.keyboard.conflictKeyIds.length > 0
                            text: qsTr("Calibration conflicts: %1 key(s)").arg(App.keyboard.conflictKeyIds.length)
                            color: "#d32f2f"
                            font.bold: true
                        }
                        Rectangle {
                            width: Kirigami.Units.gridUnit * 2
                            height: Kirigami.Units.gridUnit
                            radius: 3
                            border.width: 1
                            border.color: Qt.alpha(Kirigami.Theme.textColor, 0.45)
                            color: keyboardRoot.lastPerKeyColor
                            ToolTip.visible: swatchMouse.containsMouse
                            ToolTip.text: qsTr("Last selected per-key color")
                            MouseArea {
                                id: swatchMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                acceptedButtons: Qt.NoButton
                            }
                        }
                        Button {
                            text: qsTr("Color selection")
                            enabled: keyboardRoot.selectedPerKeyIds.length > 0
                            onClicked: kbGridBatchColorDialog.open()
                        }
                        Button {
                            text: qsTr("Clear selection")
                            enabled: keyboardRoot.selectedPerKeyIds.length > 0
                            onClicked: keyboardRoot.selectedPerKeyIds = []
                        }
                        Button {
                            text: qsTr("Clear all key colors")
                            onClicked: {
                                keyboardRoot.selectedPerKeyIds = []
                                App.keyboard.clearKeyGrid()
                            }
                        }
                    }
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Layout.fillWidth: true
                    width: parent.width
                    Kirigami.Heading {
                        level: 4
                        text: qsTr("Software (user): animation file")
                    }
                    Label {
                        text: qsTr("Runs the DSL script on the keyboard. Independent of the Apply button (palette and per-key only).")
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        font.italic: true
                    }
                    Label {
                        text: App.animationFilePath.length > 0
                              ? qsTr("File: %1").arg(App.animationFilePath)
                              : qsTr("No file selected.")
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    Label {
                        text: qsTr("Repeat count runs the whole script from the file that many times (ignored when “Loop forever” is checked).")
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        font.italic: true
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing
                        Label {
                            text: qsTr("Repeat script:")
                            Layout.alignment: Qt.AlignVCenter
                        }
                        SpinBox {
                            id: animLoops
                            from: 1
                            to: 999
                            value: 1
                            Layout.alignment: Qt.AlignVCenter
                        }
                        CheckBox {
                            id: animForever
                            text: qsTr("Loop forever")
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Button {
                            text: qsTr("Pick file…")
                            onClicked: kbAnimDialog.open()
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Button {
                            text: qsTr("Play")
                            enabled: App.animationFilePath.length > 0 && App.keyboard.connected
                            onClicked: App.keyboard.playAnimationFile(App.animationFilePath, animLoops.value, animForever.checked)
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Button {
                            text: qsTr("Stop animation")
                            onClicked: App.keyboard.stopFollowOrAnimation()
                            Layout.alignment: Qt.AlignVCenter
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
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Layout.fillWidth: true
                    width: parent.width
                    Kirigami.Heading {
                        level: 4
                        text: qsTr("Software (user): follow screen")
                    }
                    Label {
                        text: qsTr("Follow-screen does not require a firmware effect first; it switches the keyboard to user mode and samples the display.")
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        font.italic: true
                    }
                    Label {
                        text: qsTr("Independent of the Apply button (palette and per-key only).")
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        font.italic: true
                    }
                    Label {
                        visible: App.keyboard.followScreenExtraOk && App.keyboard.followScreenUsesWaylandPicker
                        text: qsTr("Wayland: a window picker will open; colors follow the selected window (not the whole desktop).")
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    ColumnLayout {
                        visible: App.keyboard.followScreenExtraOk
                        Layout.fillWidth: true
                        CheckBox {
                            id: folFull
                            text: qsTr("Fullscreen / full capture region (X11)")
                            checked: true
                            enabled: !App.keyboard.followScreenUsesWaylandPicker
                        }
                        Flow {
                            visible: !App.keyboard.followScreenUsesWaylandPicker
                            Layout.fillWidth: true
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
                                text: qsTr("Start following")
                                onClicked: App.keyboard.startFollowScreen(folFull.checked, fx.value, fy.value, fw.value, fh.value)
                            }
                            Button {
                                text: qsTr("Stop following")
                                onClicked: App.keyboard.stopFollowOrAnimation()
                            }
                        }
                    }
                    Label {
                        visible: !App.keyboard.followScreenExtraOk
                        text: qsTr("Follow screen needs: uv sync --extra screen (X11: Xlib+Pillow; Wayland: portal+pipewire-capture)")
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Layout.fillWidth: true
                    width: parent.width
                    Kirigami.Heading {
                        level: 4
                        text: qsTr("Calibration")
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            text: qsTr("Keyboard layout profile")
                        }
                        ComboBox {
                            id: layoutProfileCombo
                            Layout.fillWidth: true
                            objectName: "keyboardLayoutProfileCombo"
                            model: App.keyboard.listLayoutProfileIds()
                            onActivated: function (index) {
                                App.keyboard.setLayoutProfileId(layoutProfileCombo.currentText)
                            }
                            function syncFromBackend() {
                                var ids = App.keyboard.listLayoutProfileIds()
                                layoutProfileCombo.model = ids
                                var current = App.keyboard.layoutProfileId
                                var idx = ids.indexOf(current)
                                if (idx >= 0)
                                    layoutProfileCombo.currentIndex = idx
                            }
                            Component.onCompleted: layoutProfileCombo.syncFromBackend()
                            Connections {
                                target: App.keyboard
                                function onLayoutProfileChanged() {
                                    layoutProfileCombo.syncFromBackend()
                                }
                            }
                        }
                    }
                    Label {
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        text: qsTr("Active profile: %1. Changing profile clears per-key colors and calibration overrides for this device.").arg(App.keyboard.layoutProfileId)
                        font.italic: true
                    }
                    Label {
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        text: qsTr("Click a grid cell to light one LED, then press the matching physical key (app window must stay focused).")
                        font.italic: true
                        opacity: App.keyboard.connected ? 1.0 : 0.6
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: qsTr("Mode") }
                        ButtonGroup { id: calibrationModeGroup }
                        RadioButton {
                            text: qsTr("Manual")
                            checked: App.keyboard.calibrationMode === "manual"
                            enabled: App.keyboard.connected
                            ButtonGroup.group: calibrationModeGroup
                            onClicked: App.keyboard.setCalibrationMode("manual")
                        }
                        RadioButton {
                            text: qsTr("Automatic")
                            checked: App.keyboard.calibrationMode === "auto"
                            enabled: App.keyboard.connected
                            ButtonGroup.group: calibrationModeGroup
                            onClicked: App.keyboard.setCalibrationMode("auto")
                        }
                        Item { Layout.fillWidth: true }
                        Button {
                            text: qsTr("Start auto")
                            visible: App.keyboard.calibrationMode === "auto"
                            enabled: App.keyboard.connected
                                    && !App.keyboard.calibrationAutoRunning
                            onClicked: App.keyboard.startAutoCalibration()
                        }
                        Button {
                            text: qsTr("Stop auto")
                            visible: App.keyboard.calibrationMode === "auto"
                                    && App.keyboard.calibrationAutoRunning
                            onClicked: App.keyboard.stopAutoCalibration()
                        }
                    }
                    CalibrationDeviceGrid {
                        id: calibrationGrid
                        keyboard: App.keyboard
                        Layout.fillWidth: true
                        onCellClicked: function (visualRow, col, hasOverride) {
                            if (hasOverride)
                                App.keyboard.selectCalibrationCellForUnbind(visualRow, col)
                            else
                                App.keyboard.selectCalibrationCell(visualRow, col)
                        }
                    }
                    FocusScope {
                        id: calibrationCapture
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        focus: keyboardRoot.subNavIndex === keyboardRoot.pageCalibration
                               && App.keyboard.calibrationListening
                        Keys.onPressed: function (event) {
                            event.accepted = true
                            if (!App.keyboard.calibrationEvdevActive) {
                                App.keyboard.commitCalibrationFromPhysicalKey(
                                    event.key, event.modifiers, event.nativeScanCode)
                            }
                        }
                    }
                    Label {
                        id: calibrationStatusLabel
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        color: {
                            if (!App.keyboard.connected)
                                return Kirigami.Theme.disabledTextColor
                            if (App.keyboard.calibrationMessage.length > 0)
                                return "#d32f2f"
                            return Kirigami.Theme.textColor
                        }
                        text: {
                            if (!App.keyboard.connected)
                                return qsTr("Connect the keyboard to calibrate.")
                            if (App.keyboard.calibrationMessage.length > 0)
                                return App.keyboard.calibrationMessage
                            if (App.keyboard.calibrationEvdevActive
                                && App.keyboard.calibrationPendingDeviceRow >= 0) {
                                if (App.keyboard.calibrationEvdevExclusive)
                                    return qsTr("Exclusive capture on laptop keyboard — press the built-in key or click it on the layout below.")
                                return qsTr("Shared capture on laptop keyboard — press the key or click it on the layout below.")
                            }
                            if (App.keyboard.calibrationAutoRunning) {
                                if (App.keyboard.calibrationAutoPaused)
                                    return qsTr("Auto calibration paused — return to this tab to continue (%1).")
                                        .arg(App.keyboard.calibrationAutoProgress)
                                if (App.keyboard.calibrationPendingDeviceRow >= 0) {
                                    var keyId = App.keyboard.calibrationPendingProfileKeyId
                                    if (keyId.length > 0)
                                        return qsTr("Auto %1 — press %2 (lit LED), click it on the layout, or mark unused.")
                                            .arg(App.keyboard.calibrationAutoProgress).arg(keyId)
                                    return qsTr("Auto %1 — press the lit key, click it on the layout, or mark unused.")
                                        .arg(App.keyboard.calibrationAutoProgress)
                                }
                                return qsTr("Auto calibration complete.")
                            }
                            if (App.keyboard.calibrationPendingDeviceRow >= 0)
                                return qsTr("LED selected: device row %1, col %2 — press the matching key or click it on the layout below.")
                                    .arg(App.keyboard.calibrationPendingDeviceRow)
                                    .arg(App.keyboard.calibrationPendingDeviceCol)
                            if (App.keyboard.calibrationSelectedVisualRow >= 0)
                                return qsTr("Cell selected for clearing — use Clear cell mapping.")
                            return qsTr("Select a cell in the grid to begin.")
                        }
                    }
                    Label {
                        visible: App.keyboard.calibrationConflictSummary.length > 0
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        text: qsTr("Shared LED in profile or calibration (red keys) — clearing overrides does not remove profile defaults:\n%1")
                            .arg(App.keyboard.calibrationConflictSummary)
                        color: "#d32f2f"
                        font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                    }
                    KeyboardLayoutView {
                        keyboard: App.keyboard
                        Layout.fillWidth: true
                        readOnly: true
                        layoutInteractive: App.keyboard.calibrationListening
                        showCalibratedBadge: true
                        calibratedKeyIds: App.keyboard.calibratedKeyIds
                        conflictKeyIds: App.keyboard.conflictKeyIds
                        onKeyActivated: function (keyId) {
                            App.keyboard.commitCalibrationFromLayoutKey(keyId)
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Button {
                            text: qsTr("Mark as unused")
                            enabled: App.keyboard.connected
                                    && App.keyboard.calibrationPendingDeviceRow >= 0
                            onClicked: App.keyboard.markCalibrationCellUnused()
                        }
                        Button {
                            text: qsTr("Clear cell mapping")
                            enabled: App.keyboard.connected
                                    && App.keyboard.calibrationSelectedVisualRow >= 0
                            onClicked: App.keyboard.clearCalibrationCell(
                                App.keyboard.calibrationSelectedVisualRow,
                                App.keyboard.calibrationSelectedCol)
                        }
                        Button {
                            text: qsTr("Undo last match")
                            enabled: App.keyboard.calibrationCanUndo
                            onClicked: App.keyboard.undoLastCalibration()
                        }
                        Button {
                            text: qsTr("Clear all mappings")
                            enabled: App.keyboard.connected
                                    && (App.keyboard.calibratedKeyIds.length > 0
                                        || App.keyboard.calibrationCanUndo)
                            onClicked: App.keyboard.resetCalibrationProfile()
                        }
                    }
                    Connections {
                        target: keyboardRoot
                        function onSubNavIndexChanged() {
                            if (keyboardRoot.subNavIndex === keyboardRoot.pageCalibration)
                                App.keyboard.resumeAutoCalibration()
                            else
                                App.keyboard.pauseAutoCalibration()
                        }
                    }
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Layout.fillWidth: true
                    width: parent.width
                    Kirigami.Heading {
                        level: 4
                        text: qsTr("Extra / tools")
                    }
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
                ToolTip.text: qsTr("Turn keyboard backlight off.")
                enabled: App.keyboard.connected
                onClicked: App.keyboard.powerOff()
            }
            Item {
                Layout.fillWidth: true
            }
            Button {
                id: keyboardApplyConfigButton
                objectName: "keyboardApplyConfig"
                visible: keyboardRoot.subNavIndex === keyboardRoot.pagePalette
                    || keyboardRoot.subNavIndex === keyboardRoot.pagePerKey
                text: qsTr("Apply")
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Apply palette slot RGB or the per-key grid. Firmware applies automatically; solid colour applies automatically on its tab.")
                enabled: visible && App.keyboard.connected
                onClicked: keyboardRoot.applyKeyboardConfiguration()
            }
        }
        }
    }

    Connections {
        target: App.keyboard
        function onInspectChanged() {
            if (kbDeviceBright.sliderPressed)
                return
            kbDeviceBright.value = keyboardRoot.brightnessFwToPercent(App.keyboard.brightnessRead)
        }
    }

    Connections {
        target: keyboardRoot
        function onSubNavIndexChanged() {
            fwEffectApplyTimer.stop()
            solidApplyTimer.stop()
            keyboardRoot.solidApplyPending = false
            if (keyboardRoot.subNavIndex !== keyboardRoot.pageFirmware)
                keyboardRoot.firmwareEffectDirty = false
        }
    }
}
