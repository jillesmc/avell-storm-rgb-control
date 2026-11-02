import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import org.kde.kirigami as Kirigami
import components

/**
 * One Tuya bulb: real state only (ADR-002). Unknown → "Reading…" with disabled controls.
 * Re-reads App.bulbs.bulb(bulbId) on App.bulbs.bulbEpoch.
 */
Kirigami.Page {
    id: bulbRoot
    objectName: "bulbPage"
    title: ""

    property string bulbId: ""
    readonly property var snap: {
        var _ = App.bulbs.bulbEpoch
        return bulbRoot.bulbId.length > 0 ? App.bulbs.bulb(bulbRoot.bulbId) : ({})
    }
    readonly property bool known: snap.stateKnown === true
    readonly property bool unavailable: (snap.unavailableReason || "").length > 0
    readonly property bool controlsEnabled: known && !unavailable

    /** "none" plus the sources this runtime supports; the saved choice stays listed while paused. */
    readonly property var followSources: {
        var _ = App.bulbs.bulbEpoch + App.deviceConnectionEpoch
        return bulbRoot.bulbId.length > 0 ? App.bulbs.availableFollowSources(bulbRoot.bulbId) : []
    }
    readonly property var followOptions: {
        var out = ["none"].concat(bulbRoot.followSources)
        var saved = snap.follow || "none"
        if (out.indexOf(saved) < 0)
            out.push(saved)
        return out
    }

    function followLabel(source) {
        if (source === "keyboard") return qsTr("Keyboard")
        if (source === "screen") return qsTr("Screen")
        if (source === "led_bar") return qsTr("LED bar")
        return qsTr("None")
    }

    function followMessage() {
        var source = snap.follow || "none"
        if (source === "none")
            return ""
        var what = source === "keyboard" ? qsTr("the keyboard")
                 : (source === "screen" ? qsTr("the screen") : qsTr("the LED bar"))
        var text = qsTr("Following %1. Other apps on your network can't control this bulb locally while it follows.").arg(what)
        if (bulbRoot.followSources.indexOf(source) < 0)
            text += " " + qsTr("Paused: %1 not connected.").arg(bulbRoot.followLabel(source))
        else if (bulbRoot.known && snap.lightOn !== true)
            text += " " + qsTr("Paused while the light is off.")
        return text
    }

    property int pendingBrightness: -1
    property color pendingColor: "black"
    property bool colorDirty: false

    function modeText(mode) {
        if (mode === "white") return qsTr("White")
        if (mode === "colour") return qsTr("Colour")
        if (mode === "scene") return qsTr("Scene")
        if (mode === "music") return qsTr("Music")
        return qsTr("Unknown")
    }

    function statusLine() {
        if (!bulbRoot.known)
            return qsTr("Reading…")
        var parts = [snap.lightOn ? qsTr("On") : qsTr("Off"), modeText(snap.mode)]
        if ((snap.ip || "").length > 0)
            parts.push(snap.ip)
        return parts.join(" · ")
    }

    /* 200 ms debounce, last value wins (KeyboardPage pattern). */
    Timer {
        id: brightnessDebounce
        interval: 200
        onTriggered: {
            if (bulbRoot.pendingBrightness > 0)
                App.bulbs.setBrightness(bulbRoot.bulbId, bulbRoot.pendingBrightness)
            bulbRoot.pendingBrightness = -1
        }
    }
    Timer {
        id: colorDebounce
        interval: 200
        onTriggered: {
            if (!bulbRoot.colorDirty)
                return
            bulbRoot.colorDirty = false
            var c = bulbRoot.pendingColor
            App.bulbs.setColor(bulbRoot.bulbId, Math.round(c.r * 255), Math.round(c.g * 255), Math.round(c.b * 255))
        }
    }
    Timer {
        id: temperatureDebounce
        property int value: 0
        interval: 200
        onTriggered: App.bulbs.setWhite(bulbRoot.bulbId, value)
    }

    function requestBrightness(v) {
        bulbRoot.pendingBrightness = v
        brightnessDebounce.restart()
    }
    function requestColor(c) {
        bulbRoot.pendingColor = c
        bulbRoot.colorDirty = true
        colorDebounce.restart()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Kirigami.Units.largeSpacing
        visible: !bulbRoot.unavailable
        spacing: Kirigami.Units.largeSpacing

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.largeSpacing
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                Kirigami.Heading {
                    level: 2
                    text: snap.title || ""
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Label {
                    objectName: "bulbStatusLine"
                    text: bulbRoot.statusLine()
                    color: bulbRoot.known ? Kirigami.Theme.textColor : Kirigami.Theme.disabledTextColor
                    Layout.fillWidth: true
                }
            }
            Switch {
                objectName: "bulbPageSwitch"
                checked: bulbRoot.known && snap.lightOn === true
                enabled: bulbRoot.controlsEnabled
                Accessible.name: qsTr("Bulb light")
                onToggled: App.bulbs.setLightOn(bulbRoot.bulbId, checked)
            }
        }

        Label {
            visible: bulbRoot.known && snap.lightOn !== true
            text: qsTr("Changing brightness, temperature or colour switches the light on.")
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            font.pixelSize: Kirigami.Theme.smallFont.pixelSize
            color: Kirigami.Theme.disabledTextColor
        }

        Kirigami.InlineMessage {
            objectName: "bulbFollowMessage"
            Layout.fillWidth: true
            type: Kirigami.MessageType.Information
            text: bulbRoot.followMessage()
            visible: text.length > 0
        }

        Kirigami.FormLayout {
            Layout.fillWidth: true
            enabled: bulbRoot.controlsEnabled

            ComboBox {
                objectName: "bulbFollowCombo"
                Kirigami.FormData.label: qsTr("Follow:")
                model: bulbRoot.followOptions
                displayText: bulbRoot.followLabel(currentValue)
                currentIndex: Math.max(0, bulbRoot.followOptions.indexOf(snap.follow || "none"))
                delegate: ItemDelegate {
                    required property var modelData
                    width: ListView.view ? ListView.view.width : implicitWidth
                    text: bulbRoot.followLabel(modelData)
                }
                onActivated: function (index) {
                    App.bulbs.setFollow(bulbRoot.bulbId, bulbRoot.followOptions[index])
                }
            }

            Kirigami.Chip {
                Kirigami.FormData.label: qsTr("Mode:")
                text: bulbRoot.modeText(snap.mode)
                checkable: false
                closable: false
            }

            SliderSpinRow {
                objectName: "bulbBrightnessRow"
                Kirigami.FormData.label: qsTr("Brightness (%):")
                showLabel: false
                from: 1
                to: 100
                value: Math.max(1, snap.brightness || 1)
                Layout.fillWidth: true
                onUserAdjusted: function (v) { bulbRoot.requestBrightness(v) }
            }

            RowLayout {
                Kirigami.FormData.label: qsTr("White temperature:")
                Layout.fillWidth: true
                Label { text: qsTr("Warm") }
                SliderSpinRow {
                    objectName: "bulbTemperatureRow"
                    showLabel: false
                    from: 0
                    to: 100
                    value: snap.temperature >= 0 ? snap.temperature : 50
                    Layout.fillWidth: true
                    onUserAdjusted: function (v) {
                        temperatureDebounce.value = v
                        temperatureDebounce.restart()
                    }
                }
                Label { text: qsTr("Cold") }
            }

            ColorWell {
                objectName: "bulbColorWell"
                Kirigami.FormData.label: qsTr("Colour:")
                fillColor: (snap.rgb || []).length === 3
                           ? Qt.rgba(snap.rgb[0] / 255, snap.rgb[1] / 255, snap.rgb[2] / 255, 1)
                           : Kirigami.Theme.backgroundColor
                toolTipText: qsTr("Pick a colour")
                onClicked: bulbColorDialog.open()
            }
        }

        Item { Layout.fillHeight: true }
    }

    ColorDialog {
        id: bulbColorDialog
        title: qsTr("Bulb colour")
        onAccepted: bulbRoot.requestColor(selectedColor)
    }

    DeviceUnavailablePanel {
        objectName: "bulbUnavailable"
        anchors.fill: parent
        visible: bulbRoot.unavailable
        deviceTitle: snap.title || ""
        reason: snap.unavailableReason || ""
        forgetHint: qsTr("Stop reconnecting this bulb. Its key is kept.")
        onRetryRequested: App.bulbs.retryBulb(bulbRoot.bulbId)
        onForgetRequested: App.bulbs.forgetBulb(bulbRoot.bulbId)
    }
}
