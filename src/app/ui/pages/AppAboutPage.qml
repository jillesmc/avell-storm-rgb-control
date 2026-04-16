import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

/**
 * About: credits, licenses, upstream references (see LICENSE and NOTICE in the repo).
 * Manual layout so text wraps to the scroll viewport width (AboutItem alone was overflowing).
 */
Kirigami.Page {
    id: aboutRoot
    objectName: "aboutPage"
    title: ""

    /** Single margin source: page padding only (ScrollView fills content area). */
    leftPadding: Kirigami.Units.largeSpacing
    rightPadding: Kirigami.Units.largeSpacing
    topPadding: Kirigami.Units.largeSpacing
    bottomPadding: Kirigami.Units.largeSpacing

    background: Rectangle {
        color: "transparent"
    }

    ScrollView {
        id: aboutScroll
        anchors.fill: parent
        clip: true

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
        }
        ScrollBar.horizontal: ScrollBar {
            policy: ScrollBar.AlwaysOff
        }

        ColumnLayout {
            id: aboutColumn
            width: aboutScroll.availableWidth
            spacing: Kirigami.Units.largeSpacing

            Kirigami.Heading {
                level: 1
                Layout.fillWidth: true
                text: "Avell Storm RGB " + App.applicationVersion
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: qsTr("ITE 8291 keyboard + ITE 8233 LED bar control")
                font.bold: false
            }

            Kirigami.Separator { Layout.fillWidth: true }

            Kirigami.Heading {
                level: 2
                Layout.fillWidth: true
                text: qsTr("Copyright and notices")
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: qsTr("Third-party and protocol references are summarized in the repository file NOTICE (ite8291r3-ctl, ite8233-ledbar). The full GPL-2.0 license text is in LICENSE.")
            }

            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: qsTr("See LICENSE and NOTICE in the repository.")
            }

            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                font.weight: Font.Medium
                text: qsTr("License: GPL-2.0-or-later")
            }

            Kirigami.Separator { Layout.fillWidth: true }

            Kirigami.Heading {
                level: 2
                Layout.fillWidth: true
                text: qsTr("License text (summary)")
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: qsTr("This program is licensed under the GNU General Public License v2.0 or later. See the LICENSE file in the source tree for the complete legal text.")
            }
        }
    }
}
