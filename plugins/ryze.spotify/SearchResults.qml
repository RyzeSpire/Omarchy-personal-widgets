import QtQuick
import qs.Commons
import qs.Ui

ListView {
  id: root
  property var items: []
  property color foreground: Color.foreground
  signal chosen(var result)
  width: parent.width
  height: Math.min(contentHeight, Style.space(195))
  spacing: Style.space(4)
  clip: true
  boundsBehavior: Flickable.StopAtBounds
  model: items
  delegate: Button {
    required property var modelData
    width: root.width
    height: Style.space(50)
    foreground: root.foreground
    focusable: true
    onClicked: root.chosen(modelData)
    Row {
      anchors.fill: parent
      anchors.margins: Style.space(6)
      spacing: Style.space(10)
      Rectangle {
        width: Style.space(38)
        height: width
        color: Style.normalFillFor(root.foreground, Color.accent)
        Image {
          id: cover
          anchors.fill: parent
          source: modelData.cover || ""
          fillMode: Image.PreserveAspectCrop
          asynchronous: true
          sourceSize.width: 76
          sourceSize.height: 76
        }
        Text {
          anchors.centerIn: parent
          visible: cover.status !== Image.Ready
          text: "󰝚"
          color: Qt.darker(root.foreground, 1.5)
          font.family: Style.font.family
          font.pixelSize: Style.font.iconLarge
        }
      }
      Column {
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width - Style.space(48)
        spacing: Style.space(3)
        Text {
          width: parent.width
          textFormat: Text.PlainText
          text: modelData.name
          color: root.foreground
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          elide: Text.ElideRight
        }
        Text {
          width: parent.width
          textFormat: Text.PlainText
          text: modelData.detail
          color: Qt.darker(root.foreground, 1.5)
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
          elide: Text.ElideRight
        }
      }
    }
  }
}
