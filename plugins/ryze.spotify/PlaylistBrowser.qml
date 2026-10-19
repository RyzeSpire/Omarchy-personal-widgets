import QtQuick
import qs.Commons
import qs.Ui

Column {
  id: root
  property var playlist: ({})
  property color foreground: Color.foreground
  readonly property color muted: Qt.darker(foreground, 1.5)
  property bool loading: false
  property bool busy: false
  property bool playbackConnected: false
  property bool playing: false
  property bool shuffleOn: false
  property bool shuffleAvailable: false
  property string currentUri: ""
  property string error: ""
  readonly property var tracks: (playlist.items || []).filter(function(t) {
    var q = filter.text.trim().toLowerCase()
    return (t.name + " " + t.artist).toLowerCase().indexOf(q) !== -1
  })
  signal backRequested()
  signal openRequested()
  signal refreshRequested()
  signal authorizeRequested()
  signal playRequested(int position)
  signal shuffleRequested()
  spacing: Style.space(10)
  function reset() { filter.text = ""; songs.positionViewAtBeginning() }
  function totalDuration(ms) {
    var minutes = Math.floor(ms / 60000)
    return minutes >= 60 ? Math.floor(minutes / 60) + " hr " + minutes % 60 + " min" : minutes + " min"
  }
  Item {
    width: parent.width
    height: back.implicitHeight
    Button {
      id: back
      text: "Playlists"
      iconText: "\u{f0141}"
      foreground: root.muted
      focusable: true
      horizontalPadding: Style.space(5)
      onClicked: root.backRequested()
    }
    Button {
      anchors.right: parent.right
      text: "Open in Spotify"
      foreground: root.muted
      fontSize: Style.font.bodySmall
      focusable: true
      horizontalPadding: Style.space(5)
      onClicked: root.openRequested()
    }
  }
  Row {
    width: parent.width
    spacing: Style.space(12)
    Rectangle {
      width: Style.space(84)
      height: width
      color: Style.normalFillFor(root.foreground, Color.accent)
      radius: Style.cornerRadius
      clip: true
      Image {
        anchors.fill: parent
        source: root.playlist.cover || ""
        asynchronous: true
        fillMode: Image.PreserveAspectCrop
        sourceSize.width: 168
        sourceSize.height: 168
      }
    }
    Column {
      width: parent.width - Style.space(96)
      anchors.verticalCenter: parent.verticalCenter
      spacing: Style.space(4)
      Text {
        text: root.playlist.public === false ? "Private playlist" : "Playlist"
        color: root.muted
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
      }
      Text {
        width: parent.width
        textFormat: Text.PlainText
        text: root.playlist.name || "Playlist"
        color: root.foreground
        font.family: Style.font.family
        font.pixelSize: Style.font.heading
        font.bold: true
        wrapMode: Text.Wrap
        maximumLineCount: 2
        elide: Text.ElideRight
      }
      Text {
        width: parent.width
        textFormat: Text.PlainText
        text: root.playlist.owner || ""
        visible: text !== ""
        color: root.muted
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        elide: Text.ElideRight
      }
      Text {
        width: parent.width
        text: root.playlist.total !== undefined
          ? root.playlist.total + " songs · " + root.totalDuration(root.playlist.duration_ms || 0) : "Loading songs…"
        color: root.muted
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        wrapMode: Text.WordWrap
      }
    }
  }
  Text {
    width: parent.width
    textFormat: Text.PlainText
    text: root.playlist.description || ""
    visible: text !== ""
    color: root.muted
    font.family: Style.font.family
    font.pixelSize: Style.font.bodySmall
    wrapMode: Text.WordWrap
    maximumLineCount: 2
    elide: Text.ElideRight
  }
  Text {
    width: parent.width
    visible: (root.playlist.local_count || 0) > 0
    text: root.playlist.local_count + " local songs · Played by Spotify desktop. Files must be available in Spotify’s Local Files library."
    color: root.muted
    font.family: Style.font.family
    font.pixelSize: Style.font.caption
    wrapMode: Text.WordWrap
  }
  Row {
    spacing: Style.space(8)
    Button {
      text: root.playbackConnected ? (root.playing ? "Pause" : "Play playlist") : "Enable playback"
      iconText: root.playing ? "\u{f03e4}" : "\u{f040a}"
      foreground: "#1DB954"
      bordered: true
      focusable: true
      enabled: !root.loading && !root.busy && (root.playlist.items || []).length > 0
      opacity: enabled ? 1 : 0.4
      onClicked: { if (root.playbackConnected) root.playRequested(-1); else root.authorizeRequested() }
    }
    Button {
      iconText: "\u{f049f}"
      foreground: root.shuffleOn ? "#1DB954" : root.muted
      tooltipText: root.shuffleOn ? "Shuffle on" : "Shuffle off"
      Accessible.name: tooltipText
      focusable: true
      enabled: root.shuffleAvailable
      opacity: enabled ? 1 : 0.4
      onClicked: root.shuffleRequested()
    }
    Button {
      iconText: "\u{f0450}"
      tooltipText: "Refresh playlist"
      Accessible.name: tooltipText
      foreground: root.muted
      focusable: true
      enabled: !root.loading
      onClicked: root.refreshRequested()
    }
  }
  TextField {
    id: filter
    width: parent.width
    foreground: root.foreground
    placeholderText: "Search this playlist"
    visible: (root.playlist.items || []).length > 5
    Keys.onEscapePressed: root.backRequested()
  }
  Text {
    width: parent.width
    text: root.loading ? "Loading songs…" : root.error || ((root.playlist.items || []).length === 0 ? "This playlist has no available songs." : "No matching songs.")
    visible: root.loading || root.error !== "" || root.tracks.length === 0
    color: root.muted
    font.family: Style.font.family
    font.pixelSize: Style.font.bodySmall
    wrapMode: Text.WordWrap
  }
  TrackList {
    id: songs
    width: parent.width
    height: root.tracks.length > 0 ? Math.min(Math.max(contentHeight, Style.space(54)), Style.space(280)) : 0
    items: root.tracks
    foreground: root.foreground
    currentUri: root.currentUri
    numbered: true
    busy: root.busy || root.loading
    onChosen: function(track) {
      if (root.playbackConnected) root.playRequested(track.position)
      else root.authorizeRequested()
    }
  }
}
