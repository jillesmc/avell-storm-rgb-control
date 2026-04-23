import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

GridLayout {
    id: root

    /** Emitted when the user moves the slider or edits the spin box (not on programmatic value sync). */
    signal userAdjusted(int value)

    rowSpacing: Kirigami.Units.smallSpacing
    columnSpacing: Kirigami.Units.smallSpacing
    /** Without a leading label, always keep slider + spin on one row (never stack to two rows). */
    readonly property int layoutColumns: root.showLabel
        ? (root.width < Kirigami.Units.gridUnit * 28 ? 1 : 3)
        : 2
    columns: layoutColumns

    /** When true (and no leading label), SpinBox is placed before the Slider in the row. */
    property bool spinBeforeSlider: false

    property alias label: lbl.text
    /** When false, hide the leading label (e.g. when using Kirigami.FormLayout FormData.label). */
    property bool showLabel: true
    property int from: 0
    property int to: 100
    property int value: 0
    property int sliderMinimumWidth: 160
    readonly property int sliderRowHeight: Math.round(Kirigami.Units.gridUnit * 1.5)
    readonly property bool sliderPressed: sl.pressed

    Label {
        id: lbl
        visible: root.showLabel
        Layout.fillWidth: root.layoutColumns === 1
        Layout.preferredWidth: root.layoutColumns === 1 ? -1 : (root.showLabel ? Math.round(Kirigami.Units.gridUnit * 11) : 0)
        Layout.alignment: Qt.AlignVCenter
        Layout.column: 0
        Layout.row: 0
        elide: Text.ElideRight
        color: Kirigami.Theme.textColor
    }
    Slider {
        id: sl
        from: root.from
        to: root.to
        stepSize: 1
        value: root.value
        Layout.minimumWidth: root.sliderMinimumWidth
        Layout.preferredHeight: root.sliderRowHeight
        implicitHeight: root.sliderRowHeight
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignVCenter
        Layout.column: {
            if (root.showLabel) {
                if (root.layoutColumns === 1)
                    return 0
                return 1
            }
            return root.spinBeforeSlider ? 1 : 0
        }
        Layout.row: {
            if (root.showLabel && root.layoutColumns === 1)
                return 1
            return 0
        }
        onMoved: {
            var v = Math.round(value)
            root.value = v
            root.userAdjusted(v)
        }
    }
    SpinBox {
        id: sp
        from: root.from
        to: root.to
        value: root.value
        editable: true
        Layout.alignment: Qt.AlignVCenter
        Layout.column: {
            if (root.showLabel) {
                if (root.layoutColumns === 1)
                    return 0
                return 2
            }
            return root.spinBeforeSlider ? 0 : 1
        }
        Layout.row: {
            if (root.showLabel && root.layoutColumns === 1)
                return 2
            return 0
        }
        onValueModified: {
            root.value = value
            root.userAdjusted(value)
        }
    }
}
