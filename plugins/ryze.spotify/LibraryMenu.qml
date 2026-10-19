import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

Column {
  id: root
  property color foreground: Color.foreground
  readonly property color muted: Qt.darker(foreground, 1.5)
  property var items: []
  property bool connected: false
  signal connectionChanged(bool connected)
  property bool adding: false
  property string error: ""
  property string operation: ""
  readonly property bool busy: helper.running
  readonly property bool editing: linkField.activeFocus || nameField.activeFocus || filterField.activeFocus
  readonly property var filteredItems: {
    var q = filterField.text.trim().toLowerCase()
    return items.filter(function(item) { return item.name.toLowerCase().indexOf(q) !== -1 })
  }
  readonly property string helperPath: Quickshell.env("HOME") + "/.config/omarchy/plugins/ryze.spotify/spotify_library.py"
  signal chosen(var playlist)
  signal backRequested()

  spacing: Style.space(10)
  function run(action, args) {
    if (busy) return
    error = ""
    operation = action
    helper.command = ["python", helperPath, action].concat(args || [])
    helper.running = true
  }
  function refresh(fresh) { run("list", fresh ? ["fresh"] : []) }
  function add() { adding = true; error = ""; Qt.callLater(function() { linkField.forceActiveFocus() }) }
  function save() { run("save", [linkField.text.trim(), nameField.text.trim()]) }
  function reset() { adding = false; error = ""; filterField.text = "" }

  Process {
    id: helper
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var result = JSON.parse(text)
          if (!result.ok) { root.error = result.error; return }
          root.items = result.items || []
          root.connected = result.connected === true
          root.connectionChanged(root.connected)
          if (root.operation === "save") {
            root.adding = false
            linkField.text = ""
            nameField.text = ""
          }
        } catch (e) { root.error = "Could not load your saved playlists. Please try again." }
      }
    }
  }

  Item {
    width: parent.width
    height: addButton.implicitHeight
    Text {
      anchors.left: parent.left
      anchors.verticalCenter: parent.verticalCenter
      text: root.connected ? "Your playlists" : "Saved playlists"
      color: root.foreground
      font.family: Style.font.family
      font.pixelSize: Style.font.body
      font.bold: true
    }
    Button {
      id: addButton
      anchors.right: parent.right
      text: root.connected ? "Refresh" : "Add playlist"
      iconText: root.connected ? "󰑐" : "+"
      foreground: root.foreground
      focusable: true
      enabled: !root.busy
      visible: !root.adding
      onClicked: { if (root.connected) root.refresh(true); else root.add() }
    }
  }

  TextField {
    id: filterField
    width: parent.width
    visible: root.items.length > 3 && !root.adding
    placeholderText: "Filter playlists"
    foreground: root.foreground
    Keys.onEscapePressed: root.backRequested()
  }

  Text {
    width: parent.width
    visible: !root.adding && root.items.length === 0 && !root.busy
    text: root.connected ? "No playlists found in your Spotify account." : "Connect Spotify to load your library, or add a playlist link."
    color: root.muted
    font.family: Style.font.family
    font.pixelSize: Style.font.bodySmall
    wrapMode: Text.WordWrap
  }
  Text {
    visible: root.busy && root.operation === "list"
    text: "Loading playlists…"
    color: root.muted
    font.family: Style.font.family
    font.pixelSize: Style.font.bodySmall
  }

  ListView {
    id: playlistList
    width: parent.width
    height: visible ? Math.min(contentHeight, Style.space(170)) : 0
    visible: !root.adding && root.filteredItems.length > 0
    model: root.filteredItems
    spacing: Style.space(4)
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    delegate: Item {
      required property var modelData
      width: playlistList.width
      height: Style.space(48)
      Button {
        anchors.left: parent.left
        anchors.right: modelData.source === "shortcut" ? removeButton.left : parent.right
        anchors.rightMargin: Style.space(6)
        height: parent.height
        foreground: root.foreground
        focusable: true
        onClicked: root.chosen(modelData)
        Row {
          anchors.fill: parent
          anchors.margins: Style.space(6)
          spacing: Style.space(10)
          Rectangle {
            width: Style.space(36)
            height: width
            color: Style.normalFillFor(root.foreground, Color.accent)
            Image {
              id: cover
              anchors.fill: parent
              source: modelData.cover || ""
              fillMode: Image.PreserveAspectCrop
              asynchronous: true
              sourceSize.width: 72
              sourceSize.height: 72
            }
            Text {
              anchors.centerIn: parent
              text: "󰲸"
              visible: cover.status !== Image.Ready
              color: root.muted
              font.family: Style.font.family
              font.pixelSize: Style.font.iconLarge
            }
          }
          Column {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - Style.space(46)
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
              text: "Playlist"
              color: root.muted
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
            }
          }
        }
      }
      PanelActionButton {
        id: removeButton
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        visible: modelData.source === "shortcut"
        iconText: "×"
        tooltipText: "Remove shortcut"
        foreground: root.muted
        focusable: true
        enabled: !root.busy
        onClicked: root.run("remove", [modelData.uri])
      }
    }
  }

  Text {
    visible: !root.adding && root.items.length > 0 && root.filteredItems.length === 0
    text: "No matching playlists"
    color: root.muted
    font.family: Style.font.family
    font.pixelSize: Style.font.bodySmall
  }

  Column {
    visible: root.adding
    width: parent.width
    spacing: Style.space(8)
    TextField {
      id: linkField
      width: parent.width
      foreground: root.foreground
      placeholderText: "Paste a Spotify playlist link"
      enabled: !root.busy
      onAccepted: if (text.trim()) root.save()
      Keys.onEscapePressed: { root.adding = false; root.error = "" }
    }
    TextField {
      id: nameField
      width: parent.width
      foreground: root.foreground
      placeholderText: "Name (optional)"
      enabled: !root.busy
      onAccepted: if (linkField.text.trim()) root.save()
      Keys.onEscapePressed: { root.adding = false; root.error = "" }
    }
    Row {
      spacing: Style.space(8)
      Button {
        text: root.busy ? "Saving…" : "Save playlist"
        foreground: root.foreground
        bordered: true
        focusable: true
        enabled: !root.busy && linkField.text.trim() !== ""
        opacity: enabled ? 1 : 0.4
        onClicked: root.save()
      }
      Button {
        text: "Cancel"
        foreground: root.muted
        focusable: true
        enabled: !root.busy
        onClicked: { root.adding = false; root.error = "" }
      }
    }
  }

  Text {
    width: parent.width
    visible: root.error !== ""
    text: root.error
    color: root.foreground
    font.family: Style.font.family
    font.pixelSize: Style.font.bodySmall
    wrapMode: Text.WordWrap
  }
}
