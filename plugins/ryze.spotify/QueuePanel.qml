import QtQuick
import qs.Commons
import qs.Ui

Item {
  id: root
  property color foreground: Color.foreground
  readonly property color muted: Qt.darker(foreground, 1.5)
  property var queue: ({items: []})
  property string title: "Nothing playing"
  property string artist: ""
  property string cover: ""
  property string currentUri: ""
  property bool busy: false
  property bool loading: false
  property bool connected: false
  property string error: ""
  signal playRequested(var track)
  signal closeRequested()
  signal refreshRequested()
  signal authorizeRequested()
  Column {
    id: heading
    width: parent.width
    spacing: Style.space(10)
    Item {
      width: parent.width
      height: closeButton.implicitHeight
      Text {
        anchors.verticalCenter: parent.verticalCenter
        text: root.busy ? "Jumping…" : "Queue"
        color: root.foreground
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        font.bold: true
      }
      Row {
        anchors.right: parent.right
        Button {
          iconText: "\u{f0450}"
          foreground: root.muted
          tooltipText: "Refresh queue"
          Accessible.name: tooltipText
          horizontalPadding: Style.space(4)
          iconSpinning: root.loading || root.busy
          enabled: root.connected && !root.loading && !root.busy
          opacity: enabled ? 1 : 0.3
          onClicked: root.refreshRequested()
        }
        Button {
          id: closeButton
          text: "×"
          foreground: root.muted
          tooltipText: "Close queue"
          Accessible.name: tooltipText
          horizontalPadding: Style.space(4)
          focusable: true
          onClicked: root.closeRequested()
        }
      }
    }
    Text {
      text: "Now playing"
      color: root.muted
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
    }
    Row {
      width: parent.width
      spacing: Style.space(10)
      Rectangle {
        width: Style.space(44)
        height: width
        color: Style.normalFillFor(root.foreground, Color.accent)
        Image {
          anchors.fill: parent
          source: root.queue.current ? root.queue.current.cover : root.cover
          asynchronous: true
          fillMode: Image.PreserveAspectCrop
          sourceSize.width: 88
          sourceSize.height: 88
        }
      }
      Column {
        width: parent.width - Style.space(54)
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.space(3)
        Text {
          width: parent.width
          textFormat: Text.PlainText
          text: root.queue.current ? root.queue.current.name : root.title
          color: "#1DB954"
          font.family: Style.font.family
          font.pixelSize: Style.font.bodySmall
          elide: Text.ElideRight
        }
        Text {
          width: parent.width
          textFormat: Text.PlainText
          text: root.queue.current ? root.queue.current.artist : root.artist
          color: root.muted
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
          elide: Text.ElideRight
        }
      }
    }
    PanelSeparator { width: parent.width; foreground: root.foreground }
    Text {
      width: parent.width
      textFormat: Text.PlainText
      text: root.queue.context_name ? "Next from: " + root.queue.context_name : "Up next"
      color: root.foreground
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
      elide: Text.ElideRight
    }
    Text {
      width: parent.width
      visible: !root.connected || root.error !== "" || (root.queue.items || []).length === 0
      text: !root.connected ? "Enable playback access to see your Spotify queue."
        : root.error || (root.loading ? "Updating queue…" : root.queue.local_queue_unavailable ? "Spotify does not expose the upcoming local-file queue. Playback continues in Spotify." : "Your queue is empty.")
      color: root.muted
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
      wrapMode: Text.WordWrap
    }
    Button {
      visible: !root.connected
      text: "Enable playback access"
      foreground: root.foreground
      bordered: true
      focusable: true
      onClicked: root.authorizeRequested()
    }
  }
  TrackList {
    anchors.top: heading.bottom
    anchors.topMargin: Style.space(10)
    anchors.bottom: parent.bottom
    width: parent.width
    visible: root.connected
    items: root.queue.items || []
    foreground: root.foreground
    currentUri: root.currentUri
    clickable: true
    busy: root.busy
    opacity: root.busy ? 0.5 : 1
    onChosen: function(track) { root.playRequested(track) }
  }
}
