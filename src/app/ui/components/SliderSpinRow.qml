import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

RowLayout {
    id: root

    spacing: Kirigami.Units.smallSpacing

    property alias label: lbl.text
    /** When false, hide the leading label (e.g. when using Kirigami.FormLayout FormData.label). */
    property bool showLabel: true
    property int from: 0
    property int to: 100
    property int value: 0
    property int sliderMinimumWidth: 160

    Label {
        id: lbl
        visible: root.showLabel
        Layout.preferredWidth: root.showLabel ? Math.round(Kirigami.Units.gridUnit * 11) : 0
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
        Layout.preferredHeight: Kirigami.Units.gridUnit * 1.5
        implicitHeight: Kirigami.Units.gridUnit * 1.5
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
