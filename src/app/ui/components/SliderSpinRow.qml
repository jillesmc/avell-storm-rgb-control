import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

GridLayout {
    id: root

    rowSpacing: Kirigami.Units.smallSpacing
    columnSpacing: Kirigami.Units.smallSpacing
    columns: root.showLabel ? (root.width < Kirigami.Units.gridUnit * 28 ? 1 : 3) : (root.width < Kirigami.Units.gridUnit * 20 ? 1 : 2)

    property alias label: lbl.text
    /** When false, hide the leading label (e.g. when using Kirigami.FormLayout FormData.label). */
    property bool showLabel: true
    property int from: 0
    property int to: 100
    property int value: 0
    property int sliderMinimumWidth: 160
    readonly property int sliderRowHeight: Math.round(Kirigami.Units.gridUnit * 1.5)

    Label {
        id: lbl
        visible: root.showLabel
        Layout.fillWidth: root.columns === 1
        Layout.preferredWidth: root.columns === 1 ? -1 : (root.showLabel ? Math.round(Kirigami.Units.gridUnit * 11) : 0)
        Layout.alignment: Qt.AlignVCenter
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
        onMoved: root.value = Math.round(value)
    }
    SpinBox {
        from: root.from
        to: root.to
        value: root.value
        editable: true
        Layout.alignment: Qt.AlignVCenter
        onValueModified: root.value = value
    }
}
