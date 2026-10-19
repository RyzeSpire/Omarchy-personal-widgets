import QtQuick
import qs.Commons as Commons
import qs.Ui as Ui

Rectangle {
    id: root
    required property var game
    property bool busy: false
    property bool clientAvailable: true
    property color foreground: Commons.Color.foreground
    signal launchRequested(string appid)
    signal detailsRequested(string appid)
    signal favoriteRequested(string appid, bool enabled)
    implicitHeight: Commons.Style.space(104)
    radius: Commons.Style.cornerRadius
    color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.035)

    function sizeLabel(bytes) {
        return bytes >= 1073741824 ? (bytes / 1073741824).toFixed(1) + " GiB" : Math.round(bytes / 1048576) + " MiB"
    }

    Rectangle {
        id: cover
        x: Commons.Style.space(8)
        anchors.verticalCenter: parent.verticalCenter
        width: Commons.Style.space(56)
        height: Commons.Style.space(84)
        color: "#1b2838"
        clip: true
        Text {
            anchors.centerIn: parent
            text: "\uf1b6"
            color: "#66C0F4"
            font.family: Commons.Style.font.family
            font.pixelSize: Commons.Style.space(25)
        }
        Image {
            anchors.fill: parent
            source: root.game.artwork || ""
            asynchronous: true
            fillMode: Image.PreserveAspectCrop
        }
    }

    Column {
        anchors.left: cover.right
        anchors.leftMargin: Commons.Style.space(12)
        anchors.right: parent.right
        anchors.rightMargin: Commons.Style.space(10)
        anchors.verticalCenter: parent.verticalCenter
        spacing: Commons.Style.space(7)
        Text {
            width: parent.width
            text: root.game.name
            textFormat: Text.PlainText
            color: root.foreground
            font.family: Commons.Style.font.family
            font.pixelSize: Commons.Style.font.body
            font.bold: true
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }
        Item {
            width: parent.width
            height: actions.implicitHeight
            Text {
                anchors.left: parent.left
                anchors.right: actions.left
                anchors.rightMargin: Commons.Style.space(8)
                anchors.verticalCenter: parent.verticalCenter
                text: root.sizeLabel(root.game.size)
                color: Qt.darker(root.foreground, 1.5)
                font.family: Commons.Style.font.family
                font.pixelSize: Commons.Style.font.caption
                elide: Text.ElideRight
            }
            Row {
                id: actions
                anchors.right: parent.right
                spacing: Commons.Style.space(5)
                Ui.Button {
                    text: "View"
                    foreground: root.foreground
                    focusable: true
                    enabled: !root.busy
                    fontSize: Commons.Style.font.caption
                    onClicked: root.detailsRequested(root.game.appid)
                }
                Ui.Button {
                    text: root.game.favorite ? "★" : "☆"
                    foreground: root.game.favorite ? "#E5C07B" : root.foreground
                    tooltipText: root.game.favorite ? "Unpin from widget favorites" : "Pin to widget favorites"
                    focusable: true
                    enabled: !root.busy
                    onClicked: root.favoriteRequested(root.game.appid, !root.game.favorite)
                }
                Ui.Button {
                    text: "Play"
                    iconText: "\uf04b"
                    foreground: "#66C0F4"
                    bordered: true
                    focusable: true
                    enabled: !root.busy && root.clientAvailable
                    tooltipText: "Launch " + root.game.name + " through Steam"
                    onClicked: root.launchRequested(root.game.appid)
                }
            }
        }
    }
}
