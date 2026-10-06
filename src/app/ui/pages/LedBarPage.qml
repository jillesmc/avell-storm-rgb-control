import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import components

/**
 * LED bar: headers + scroll body by subNavIndex + footer (shell drives subNavIndex).
 */
Item {
    id: ledRoot
    objectName: "ledBarPage"
    property var appShell
    property int subNavIndex: 0
    /** Remembered but not connected (not found / USB error): body replaced by a placeholder. */
    readonly property bool deviceUnavailable: App.ledBarUnavailableReason.length > 0

    property bool ledPreferNamed: true
    property string ledPickName: ""
    property bool ledHexProgrammatic: false

    readonly property int namedSwatchTargetWidth: Kirigami.Units.gridUnit * 8
    readonly property bool narrowContent: ledScroll.availableWidth < Kirigami.Units.gridUnit * 26

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
                ledDeviceBright.value,
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

    Connections {
        target: appShell
        function onLedSelectedEffectChanged() {
            if (typeof ledTuneFx !== "undefined")
                ledTuneFx.syncFromShell()
            if (typeof ledPalFx !== "undefined")
                ledPalFx.syncFromShell()
        }
    }

    DeviceUnavailablePanel {
        objectName: "ledBarUnavailable"
        anchors.fill: parent
        visible: ledRoot.deviceUnavailable
        deviceTitle: qsTr("LED bar")
        reason: App.ledBarUnavailableReason
        onRetryRequested: App.retryDevice("led_bar")
        onForgetRequested: App.forgetDevice("led_bar")
    }

    Item {
        visible: !ledRoot.deviceUnavailable
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

            }

        Kirigami.Separator {
            Layout.fillWidth: true
        }

        ScrollView {
            id: ledScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            padding: 0
            leftPadding: 0
            readonly property int _ledScrollRightGutter: Math.max(
                Kirigami.Units.gridUnit,
                Math.ceil(ledVBar.implicitWidth + Kirigami.Units.smallSpacing))
            rightPadding: _ledScrollRightGutter
            topPadding: 0
            bottomPadding: 0

            ScrollBar.vertical: ScrollBar {
                id: ledVBar
                policy: ScrollBar.AsNeeded
                parent: ledScroll
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.right: parent.right
            }
            ScrollBar.horizontal: ScrollBar {
                policy: ScrollBar.AlwaysOff
                parent: ledScroll
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
            }

            Item {
                id: ledScrollBody
                readonly property Item currentPage: ledModeStack.itemAt(ledModeStack.currentIndex)
                implicitHeight: ledOuterColumn.implicitHeight
                width: ledScroll.availableWidth
                height: Math.round(implicitHeight)

                ColumnLayout {
                    id: ledOuterColumn
                    width: parent.width
                    spacing: Kirigami.Units.mediumSpacing

                    Kirigami.Heading {
                        level: 4
                        text: qsTr("Device")
                    }
                    Label {
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        font.italic: true
                        text: qsTr("Brightness (0–100) applies immediately and re-applies the last visual mode, or the effect selected below if none is stored yet.")
                    }
                    SliderSpinRow {
                        id: ledDeviceBright
                        label: qsTr("Brightness 0–100")
                        from: 0
                        to: 100
                        value: 50
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        sliderMinimumWidth: 72
                        enabled: App.ledBar.connected
                        onUserAdjusted: function (v) {
                            App.ledBar.requestBrightnessFromUi(v, appShell.ledSelectedEffect)
                        }
                    }

                    Kirigami.Separator {
                        Layout.fillWidth: true
                    }

                    StackLayout {
                        id: ledModeStack
                        Layout.fillWidth: true
                        currentIndex: ledRoot.subNavIndex
                        implicitHeight: {
                            var it = ledModeStack.itemAt(ledModeStack.currentIndex)
                            return it ? it.implicitHeight : Kirigami.Units.gridUnit * 20
                        }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Layout.fillWidth: true
                    width: parent.width
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
                        readonly property int columns: Math.max(1, Math.floor(width / ledRoot.namedSwatchTargetWidth))
                        readonly property real cellSize: Math.max(
                            Kirigami.Units.gridUnit * 6,
                            Math.floor((Math.max(width, 1) - spacing * (columns - 1)) / columns))
                        Repeater {
                            model: App.ledNamedColorEntries
                            delegate: Rectangle {
                                required property var modelData
                                width: ledNamedFlow.cellSize
                                height: ledNamedFlow.cellSize
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
                        Layout.fillWidth: true
                        Layout.maximumWidth: Kirigami.Units.gridUnit * 14
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
                    Layout.fillWidth: true
                    width: parent.width
                    Label {
                        text: qsTr("Preset (tap chip)")
                    }
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
                    ComboBox {
                        id: ledPalFx
                        model: App.ledEffectNames
                        Layout.fillWidth: true
                        ToolTip.visible: hovered
                        ToolTip.text: qsTr("Visual effect paired with the chosen preset colours.")
                        Component.onCompleted: ledPalFx.syncFromShell()
                        onModelChanged: ledPalFx.syncFromShell()
                        function syncFromShell() {
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
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Layout.fillWidth: true
                    width: parent.width
                    Label {
                        text: qsTr("Effect (tap a chip to select)")
                    }
                    Flow {
                        id: ledFxGrid
                        objectName: "ledBarEffectGrid"
                        Layout.fillWidth: true
                        width: parent.width
                        spacing: Kirigami.Units.smallSpacing

                        Repeater {
                            model: App.ledEffectNames
                            delegate: EffectCard {
                                required property int index
                                effectName: App.ledEffectNames[index]
                                selected: appShell.ledSelectedEffect === effectName
                                onActivated: appShell.ledSelectedEffect = effectName
                            }
                        }
                    }
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Layout.fillWidth: true
                    width: parent.width
                    ColumnLayout {
                        Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing

                        Label {
                            text: qsTr("Note:")
                        }
                        Label {
                            text: qsTr("Brightness is controlled in the Device section at the top of this page; here you set speed and which effect to pair when you press Apply.")
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Label { text: qsTr("Speed (1–10):") }
                        SliderSpinRow {
                            id: ledTuneSpeed
                            showLabel: false
                            from: 1
                            to: 10
                            value: 3
                            Layout.fillWidth: true
                            Layout.maximumWidth: Kirigami.Units.gridUnit * 12
                        }

                        Label { text: qsTr("Effect:") }
                        ComboBox {
                            id: ledTuneFx
                            model: App.ledEffectNames
                            Layout.fillWidth: true
                            Layout.maximumWidth: Kirigami.Units.gridUnit * 12
                            ToolTip.visible: hovered
                            ToolTip.text: qsTr("Effect applied after brightness and speed.")
                            Component.onCompleted: ledTuneFx.syncFromShell()
                            onModelChanged: ledTuneFx.syncFromShell()
                            function syncFromShell() {
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
