import QtCore
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import org.kde.kirigami as Kirigami

/**
 * Devices → "Smart bulbs": Import, one row per imported bulb (Connect/Disconnect/Remove).
 * Only loaded when App.bulbsAvailable (the optional tuya extra).
 */
ColumnLayout {
    id: panel
    objectName: "bulbListPanel"
    spacing: Kirigami.Units.largeSpacing

    property string pendingRemoveId: ""
    property string pendingRemoveName: ""

    function askRemove(bulbId, name) {
        panel.pendingRemoveId = bulbId
        panel.pendingRemoveName = name
        removeDialog.open()
    }
    function confirmRemove() {
        App.bulbs.removeBulb(panel.pendingRemoveId)
        panel.pendingRemoveId = ""
        removeDialog.close()
    }
    function cancelRemove() {
        panel.pendingRemoveId = ""
        removeDialog.close()
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Kirigami.Units.mediumSpacing
        Kirigami.Heading {
            level: 3
            text: qsTr("Smart bulbs")
            Layout.alignment: Qt.AlignVCenter
        }
        Kirigami.Separator {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
        }
        Button {
            objectName: "bulbImportButton"
            text: qsTr("Import Tuya devices…")
            icon.name: "document-import"
            onClicked: importDialog.open()
        }
    }

    Label {
        objectName: "bulbEmptyHint"
        visible: bulbRepeater.count === 0
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        opacity: 0.75
        text: qsTr("Import the devices.json written by the tinytuya wizard to control your Tuya bulbs.")
    }

    Label {
        objectName: "bulbImportSummary"
        visible: text.length > 0
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        text: App.bulbs.importSummary
    }

    Repeater {
        id: bulbRepeater
        model: App.bulbs.model

        delegate: Item {
            id: bulbRow
            objectName: "bulbRow_" + model.bulbId
            Layout.fillWidth: true
            implicitHeight: rowLayout.implicitHeight + Kirigami.Units.largeSpacing * 2

            Rectangle {
                anchors.fill: parent
                radius: Kirigami.Units.smallSpacing
                color: Kirigami.Theme.alternateBackgroundColor
                border.width: 1
                border.color: Qt.alpha(Kirigami.Theme.disabledTextColor, 0.22)
            }

            RowLayout {
                id: rowLayout
                anchors {
                    left: parent.left
                    right: parent.right
                    top: parent.top
                    margins: Kirigami.Units.largeSpacing
                }
                spacing: Kirigami.Units.largeSpacing

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    spacing: Kirigami.Units.smallSpacing
                    Label {
                        text: model.title
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                        color: model.remembered ? Kirigami.Theme.linkColor : Kirigami.Theme.textColor
                    }
                    Label {
                        text: model.subtitle
                        visible: text.length > 0
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                        font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                        color: model.available ? Kirigami.Theme.textColor : Kirigami.Theme.disabledTextColor
                    }
                    Label {
                        text: qsTr("Remembered — configure it from the sidebar.")
                        visible: model.remembered
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        font.pointSize: 9
                        opacity: 0.9
                    }
                }
                Button {
                    objectName: "bulbConnectButton_" + model.bulbId
                    enabled: !model.busy
                    text: model.busy ? qsTr("Connecting…")
                                     : (model.remembered ? qsTr("Disconnect") : qsTr("Connect"))
                    highlighted: model.remembered
                    Layout.minimumWidth: Kirigami.Units.gridUnit * 9
                    Layout.alignment: Qt.AlignTop
                    ToolTip.visible: hovered
                    ToolTip.text: model.remembered
                                  ? qsTr("Stop remembering this bulb. Its key is kept.")
                                  : qsTr("Read this bulb and remember it.")
                    onClicked: {
                        if (model.remembered)
                            App.bulbs.disconnectBulb(model.bulbId)
                        else
                            App.bulbs.connectBulb(model.bulbId)
                    }
                }
                Button {
                    objectName: "bulbRemoveButton_" + model.bulbId
                    icon.name: "edit-delete"
                    display: AbstractButton.IconOnly
                    text: qsTr("Remove")
                    Layout.alignment: Qt.AlignTop
                    ToolTip.visible: hovered
                    ToolTip.text: qsTr("Remove from this app (deletes its local key)")
                    onClicked: panel.askRemove(model.bulbId, model.title)
                }
            }
        }
    }

    FileDialog {
        id: importDialog
        title: qsTr("Import Tuya devices")
        fileMode: FileDialog.OpenFile
        nameFilters: [qsTr("tinytuya devices (*.json)"), qsTr("All files (*)")]
        currentFolder: StandardPaths.writableLocation(StandardPaths.HomeLocation)
        /* selectedFile is a url; the slot calls toLocalFile() — do not strip file:// here. */
        onAccepted: App.bulbs.importFile(selectedFile)
    }

    Kirigami.PromptDialog {
        id: removeDialog
        objectName: "bulbRemoveDialog"
        title: qsTr("Remove %1?").arg(panel.pendingRemoveName)
        subtitle: qsTr("Its local key is deleted from this app. You can import it again later.")
        standardButtons: Kirigami.Dialog.NoButton
        customFooterActions: [
            Kirigami.Action {
                text: qsTr("Remove")
                icon.name: "edit-delete"
                onTriggered: panel.confirmRemove()
            },
            Kirigami.Action {
                text: qsTr("Cancel")
                icon.name: "dialog-cancel"
                onTriggered: panel.cancelRemove()
            }
        ]
    }
}
