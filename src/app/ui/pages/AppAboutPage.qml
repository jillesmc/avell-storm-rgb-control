import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

/**
 * About: credits, licenses, upstream references (see LICENSE and NOTICE in the repo).
 */
Kirigami.ScrollablePage {
    id: aboutRoot
    objectName: "aboutPage"
    title: ""

    leftPadding: Kirigami.Units.largeSpacing
    rightPadding: Kirigami.Units.largeSpacing
    topPadding: Kirigami.Units.largeSpacing

    background: Rectangle {
        color: "transparent"
    }

    ColumnLayout {
        width: aboutRoot.width - aboutRoot.leftPadding - aboutRoot.rightPadding
        spacing: Kirigami.Units.largeSpacing

        Kirigami.AboutItem {
            id: aboutItem
            Layout.fillWidth: true
            wideMode: aboutRoot.width >= implicitWidth
            aboutData: ({
                displayName: "Avell Storm RGB",
                productName: "avell-storm-rgb",
                componentName: "avell-storm-rgb",
                shortDescription: qsTr("ITE 8291 keyboard + ITE 8233 LED bar control"),
                homepage: "",
                bugAddress: "",
                version: App.applicationVersion,
                otherText: qsTr("Third-party and protocol references are summarized in the repository file NOTICE (ite8291r3-ctl, ite8233-ledbar). The full GPL-2.0 license text is in LICENSE."),
                authors: [],
                credits: [],
                translators: [],
                licenses: [
                    {
                        name: "GPL-2.0-or-later",
                        spdx: "GPL-2.0-or-later",
                        text: qsTr("This program is licensed under the GNU General Public License v2.0 or later. See the LICENSE file in the source tree for the complete legal text.")
                    }
                ],
                copyrightStatement: qsTr("See LICENSE and NOTICE in the repository."),
                desktopFileName: ""
            })
        }
    }
}
