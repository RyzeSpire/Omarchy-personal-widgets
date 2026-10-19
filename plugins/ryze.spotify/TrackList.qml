import QtQuick
import qs.Commons
import qs.Ui

ListView {
  id: root
  property var items: []
  property color foreground: Color.foreground
  property string currentUri: ""
  property bool numbered: false
  property bool clickable: true
  property bool busy: false
  signal chosen(var track)
  model: items
  spacing: Style.space(3)
  clip: true
  boundsBehavior: Flickable.StopAtBounds
  function durationLabel(ms) {
    var seconds = Math.floor(ms / 1000)
    return Math.floor(seconds / 60) + ":" + (seconds % 60 < 10 ? "0" : "") + seconds % 60
  }
  delegate: Item {
    id: songRow
    required property var modelData
    readonly property bool current: modelData.uri !== "" && modelData.uri === root.currentUri
    width: root.width
    height: Style.space(54)
    opacity: modelData.playable === false ? 0.5 : 1
    Button {
      anchors.fill: parent
      visible: root.clickable
      foreground: root.foreground
      focusable: true
      enabled: modelData.playable !== false && !root.busy
      Accessible.name: "Play " + modelData.name + " by " + modelData.artist
      tooltipText: modelData.is_local ? "Play through Spotify desktop using its local music library" : ""
      onClicked: root.chosen(songRow.modelData)
    }
    Row {
      anchors.fill: parent
      anchors.margins: Style.space(6)
      spacing: Style.space(8)
      Text {
        visible: root.numbered
        width: visible ? Style.space(24) : 0
        anchors.verticalCenter: parent.verticalCenter
        text: songRow.current ? "\u{f057e}" : songRow.modelData.position + 1
        horizontalAlignment: Text.AlignHCenter
        color: songRow.current ? "#1DB954" : Qt.darker(root.foreground, 1.5)
        font.family: Style.font.family
        font.pixelSize: songRow.current ? Style.font.icon : Style.font.caption
      }
      Rectangle {
        width: Style.space(38)
        height: width
        anchors.verticalCenter: parent.verticalCenter
        color: Style.normalFillFor(root.foreground, Color.accent)
        Image {
          anchors.fill: parent
          source: songRow.modelData.cover || ""
          asynchronous: true
          fillMode: Image.PreserveAspectCrop
          sourceSize.width: 76
          sourceSize.height: 76
        }
      }
      Column {
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width - Style.space(38 + 40 + (root.numbered ? 24 + 24 : 16))
        spacing: Style.space(3)
        Text {
          width: parent.width
          textFormat: Text.PlainText
          text: songRow.modelData.name
          color: songRow.current ? "#1DB954" : root.foreground
          font.family: Style.font.family
          font.pixelSize: Style.font.bodySmall
          elide: Text.ElideRight
        }
        Text {
          width: parent.width
          textFormat: Text.PlainText
          text: songRow.modelData.artist + (songRow.modelData.is_local ? (songRow.modelData.artist ? " · " : "") + "Local file" : "")
          color: Qt.darker(root.foreground, 1.5)
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
          elide: Text.ElideRight
        }
      }
      Text {
        anchors.verticalCenter: parent.verticalCenter
        width: Style.space(40)
        text: root.durationLabel(songRow.modelData.duration_ms)
        horizontalAlignment: Text.AlignRight
        color: Qt.darker(root.foreground, 1.5)
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
      }
    }
  }
}
