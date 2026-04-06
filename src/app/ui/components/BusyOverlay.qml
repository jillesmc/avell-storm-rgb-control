import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Rectangle {
    id: root
    anchors.fill: parent
    visible: busy
    color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g,
                  Kirigami.Theme.backgroundColor.b, 0.45)
    z: 1000

    property bool busy: false

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 12

        BusyIndicator {
            Layout.alignment: Qt.AlignHCenter
            running: root.busy
        }
        Label {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("USB operation in progress…")
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }
    }
}
