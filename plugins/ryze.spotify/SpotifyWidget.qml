import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Mpris
import qs.Commons
import qs.Ui
import qs.Ui as Ui

Ui.BarWidget {
  id: root
  moduleName: "ryze.spotify"

  property bool opened: false
  readonly property bool quittingSpotify: quitProcess.running
  property bool popoutSwitchClosing: false
  property int clockTick: 0
  property string extraView: ""
  property string selectedPlaylist: ""
  property string searchError: ""
  property string playbackError: ""
  readonly property string desktopHelperPath: decodeURIComponent(Qt.resolvedUrl("spotify_desktop.py").toString().replace(/^file:\/\//, ""))
  property bool playbackConnected: false
  property bool queueOpen: true
  property var queueData: ({items: []})
  property string queueError: ""
  property int playbackGeneration: 0
  property var playlistData: ({})
  property string playlistError: ""
  readonly property string playbackHelperPath: decodeURIComponent(Qt.resolvedUrl("spotify_playback.py").toString().replace(/^file:\/\//, ""))
  readonly property string currentTrackUri: {
    var uri = player && player.metadata ? String(player.metadata["xesam:url"] || "") : ""
    var match = /^https:\/\/open\.spotify\.com\/(?:intl-[a-z]{2}\/)?(track|episode)\/([A-Za-z0-9]{22})(?:[?/#]|$)/.exec(uri)
    if (match) return "spotify:" + match[1] + ":" + match[2]
    var local = /^https:\/\/open\.spotify\.com\/(?:intl-[a-z]{2}\/)?local\/([^/]*\/[^/]*\/[^/]*\/[0-9]+)\/?(?:[?#].*)?$/.exec(uri)
    return local ? "spotify:local:" + local[1].split("/").join(":") : uri
  }
  readonly property bool queueBeside: queueOpen && panel.contentWidth >= Style.space(600)
  onQueueOpenChanged: if (queueOpen && opened) refreshQueue()
  property bool apiConnected: false
  property bool apiConfigured: false
  property string connectionError: ""
  property var searchResults: []
  property bool searched: false
  readonly property string helperPath: decodeURIComponent(Qt.resolvedUrl("spotify_library.py").toString().replace(/^file:\/\//, ""))
  readonly property var player: {
    var players = Mpris.players.values
    for (var i = 0; i < players.length; i++) {
      var p = players[i]
      if (p && (p.desktopEntry === "spotify" || /^spotify$/i.test(p.identity))) return p
    }
    return null
  }
  readonly property color foreground: bar ? bar.foreground : Color.foreground
  readonly property color muted: Qt.darker(foreground, 1.5)
  readonly property string title: player && player.trackTitle ? player.trackTitle : "Nothing playing"
  readonly property string artist: player ? player.trackArtist : ""
  readonly property string album: player ? player.trackAlbum : ""
  readonly property real duration: player && player.lengthSupported ? Math.max(0, player.length) : 0
  readonly property real position: {
    clockTick
    return player && player.positionSupported ? Math.max(0, Math.min(duration, player.position)) : 0
  }

  readonly property bool shuffleOn: !!player && player.shuffleSupported && player.shuffle
  readonly property int repeatMode: player && player.loopSupported ? player.loopState : MprisLoopState.None
  readonly property string repeatLabel: repeatMode === MprisLoopState.Track ? "Single song"
    : repeatMode === MprisLoopState.Playlist ? "Playlist" : "Off"

  readonly property bool volumeAvailable: !!player && player.canControl && player.volumeSupported
  readonly property real spotifyVolume: volumeAvailable ? Math.max(0, Math.min(1, player.volume)) : 0
  property real previousVolume: 0.5
  onSpotifyVolumeChanged: if (spotifyVolume > 0) previousVolume = spotifyVolume

  function setVolume(percent) {
    if (!volumeAvailable || !isFinite(percent)) return
    player.volume = Math.max(0, Math.min(100, percent)) / 100
  }
  function toggleMute() {
    if (!volumeAvailable) return
    if (spotifyVolume > 0) {
      previousVolume = spotifyVolume
      setVolume(0)
    } else setVolume(previousVolume * 100)
  }

  function toggleShuffle() {
    if (player && player.canControl && player.shuffleSupported)
      player.shuffle = !player.shuffle
  }
  function cycleRepeat() {
    if (!player || !player.canControl || !player.loopSupported) return
    player.loopState = repeatMode === MprisLoopState.None ? MprisLoopState.Track
      : repeatMode === MprisLoopState.Track ? MprisLoopState.Playlist : MprisLoopState.None
  }

  function suppressReveal(value) {
    if (bar && typeof bar.setCenterHoverRevealSuppressed === "function")
      bar.setCenterHoverRevealSuppressed(value)
  }
  function open() {
    if (quittingSpotify) return
    popoutSwitchClosing = false
    opened = true
    checkConnection()
    startDesktop("background")
    if (queueOpen) refreshQueue()
    Qt.callLater(function() { if (root.opened) root.suppressReveal(true) })
  }
  function close() {
    opened = false
    extraView = ""
    libraryMenu.reset()
    suppressReveal(false)
  }
  function showView(view) {
    extraView = extraView === view ? "" : view
    searchError = ""
    if (extraView === "playlists") libraryMenu.refresh()
    if (extraView === "search") Qt.callLater(function() { searchField.forceActiveFocus() })
  }
  function confirmQuit() {
    if (quittingSpotify || backgroundProcess.running || desktopProcess.running || playbackProcess.running || searchProcess.running) return
    playbackError = ""
    playbackGeneration++
    queueDebounce.stop()
    quitProcess.running = true
  }
  function openApp() {
    startDesktop("show")
    close()
  }
  function checkConnection() {
    if (!statusProcess.running) statusProcess.running = true
  }
  function connectAccount() {
    if (authProcess.running) return
    connectionError = ""
    if (!apiConfigured) {
      Quickshell.execDetached(["omarchy", "launch", "terminal", "python", helperPath, "authorize"])
      root.close()
    } else {
      authProcess.command = ["python", helperPath, "authorize"]
      authProcess.running = true
    }
  }
  function disconnectAccount() {
    authProcess.command = ["python", helperPath, "disconnect"]
    authProcess.running = true
  }
  function search() {
    if (!searchField.text.trim() || searchProcess.running) return
    searchError = ""
    searchResults = []
    searched = false
    searchProcess.command = ["python", helperPath, apiConnected ? "catalog" : "search", searchField.text.trim()]
    searchProcess.running = true
  }
  function startDesktop(action, uri) {
    if (quittingSpotify) return
    playbackError = ""
    if (action === "background") {
      if (backgroundProcess.running || desktopProcess.running) return
      backgroundProcess.running = true
    } else {
      if (desktopProcess.running) return
      desktopProcess.command = ["python", desktopHelperPath, action]
      if (uri) desktopProcess.command.push(uri)
      desktopProcess.running = true
    }
  }
  function choosePlaylist(item) {
    if (/^spotify:playlist:/.test(item.uri)) {
      selectedPlaylist = item.name
      playlistData = item
      playlistError = ""
      extraView = "playlist"
      playlistBrowser.reset()
      loadPlaylist(false)
      if (queueOpen) refreshQueue()
    } else {
      startDesktop("open-uri", item.uri)
      extraView = ""
    }
    keyCatcher.forceActiveFocus()
  }
  function loadPlaylist(fresh) {
    if (!playlistData.uri || playlistProcess.running) return
    playlistError = ""
    playlistProcess.command = ["python", playbackHelperPath, "playlist", playlistData.uri]
    if (fresh) playlistProcess.command.push("fresh")
    playlistProcess.running = true
  }
  function playPlaylist(position) {
    if (!playbackConnected) { connectAccount(); return }
    if (playbackProcess.running || !playlistData.uri) return
    if (position < 0 && queueData.context_uri === playlistData.uri && player) {
      player.togglePlaying()
      return
    }
    playbackError = ""
    playbackGeneration++
    playbackProcess.command = ["python", playbackHelperPath, "play", playlistData.uri, String(position)]
    playbackProcess.running = true
  }
  function playQueuedTrack(track) {
    if (!playbackConnected) { connectAccount(); return }
    if (playbackProcess.running || !track || !track.uri) return
    playbackError = ""
    playbackGeneration++
    playbackProcess.command = ["python", playbackHelperPath, "queue-play", track.uri, String(track.position)]
    playbackProcess.running = true
  }
  function refreshQueue() {
    if (!opened || !queueOpen || !playbackConnected || queueProcess.running || playbackProcess.running || quittingSpotify) return
    queueError = ""
    queueProcess.running = true
  }
  function openPlaylistApp() {
    startDesktop("show", playlistData.uri)
    close()
  }
  function toggle() { if (opened) close(); else open() }
  function closeForPopoutSwitch() { popoutSwitchClosing = true; close() }
  function switchPanel(direction) {
    if (bar && typeof bar.switchPanelFrom === "function") bar.switchPanelFrom(root, direction)
  }
  function playPause() {
    if (player && player.canTogglePlaying) player.togglePlaying()
    else startDesktop("play")
  }
  function timeLabel(seconds) {
    var s = Math.max(0, Math.floor(seconds))
    return Math.floor(s / 60) + ":" + (s % 60 < 10 ? "0" : "") + (s % 60)
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight
  Component.onDestruction: suppressReveal(false)

  Timer {
    interval: 1000
    running: root.opened && !!root.player && root.player.isPlaying
    repeat: true
    onTriggered: root.clockTick++
  }

  Process {
    id: backgroundProcess
    command: ["python", root.desktopHelperPath, "background"]
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var result = JSON.parse(text)
          if (!result.ok) root.playbackError = result.error
        } catch (e) { root.playbackError = "Spotify could not start in the background." }
      }
    }
  }
  Process {
    id: desktopProcess
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var result = JSON.parse(text)
          if (!result.ok) root.playbackError = result.error
        } catch (e) { root.playbackError = "Spotify could not complete this action." }
      }
    }
  }

  Process {
    id: quitProcess
    command: ["python", root.desktopHelperPath, "quit"]
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var result = JSON.parse(text)
          if (result.ok) {
            root.queueData = ({items: []})
            root.close()
          } else root.playbackError = result.error
        } catch (e) { root.playbackError = "Spotify could not quit. Please try again." }
      }
    }
  }

  Process {
    id: searchProcess
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var result = JSON.parse(text)
          if (result.ok && result.mode === "catalog") {
            root.searchResults = result.items || []
            root.searched = true
          } else if (result.ok) root.close()
          else root.searchError = result.error
        } catch (e) { root.searchError = "Spotify search could not open. Please try again." }
      }
    }
  }

  Process {
    id: statusProcess
    command: ["python", root.helperPath, "status"]
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var result = JSON.parse(text)
          if (result.ok) {
            root.apiConnected = result.connected === true
            root.apiConfigured = result.configured === true
            root.playbackConnected = result.playback_connected === true
            if (root.playbackConnected) root.refreshQueue()
            else root.queueData = ({items: []})
          } else root.connectionError = result.error
        } catch (e) { root.connectionError = "Could not read Spotify connection status." }
      }
    }
  }
  Process {
    id: authProcess
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var result = JSON.parse(text)
          if (result.ok) {
            root.apiConnected = result.connected === true
            root.apiConfigured = result.configured === true
            root.playbackConnected = result.playback_connected === true
            if (root.playbackConnected) root.refreshQueue()
            else root.queueData = ({items: []})
            root.searchResults = []
            root.searched = false
            root.connectionError = ""
            if (root.extraView === "playlists") libraryMenu.refresh(true)
          } else root.connectionError = result.error
        } catch (e) { root.connectionError = "Spotify could not connect. Please try again." }
      }
    }
  }
  Process {
    id: playlistProcess
    onExited: {
      if (root.opened && root.extraView === "playlist" && root.playlistData.uri !== command[3])
        Qt.callLater(function() { root.loadPlaylist(false) })
    }
    stdout: StdioCollector {
      onStreamFinished: {
        if (playlistProcess.command[3] !== root.playlistData.uri) return
        try {
          var result = JSON.parse(text)
          if (result.ok) root.playlistData = result.playlist
          else root.playlistError = result.error
        } catch (e) { root.playlistError = "Could not load this playlist. Please try again." }
      }
    }
  }
  Process {
    id: queueProcess
    property int requestGeneration: 0
    onRunningChanged: if (running) requestGeneration = root.playbackGeneration
    command: ["python", root.playbackHelperPath, "queue"]
    stdout: StdioCollector {
      onStreamFinished: {
        if (!root.playbackConnected || queueProcess.requestGeneration !== root.playbackGeneration) return
        try {
          var result = JSON.parse(text)
          if (result.ok) root.queueData = result.queue
          else {
            root.queueError = result.error
            if (result.needs_authorization) root.playbackConnected = false
          }
        } catch (e) { root.queueError = "Could not load your queue. Please try again." }
      }
    }
  }
  Process {
    id: playbackProcess
    onExited: queueDebounce.restart()
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var result = JSON.parse(text)
          if (result.ok) queueDebounce.restart()
          else {
            root.playbackError = result.error
            if (result.needs_authorization) root.playbackConnected = false
          }
        } catch (e) { root.playbackError = "Spotify could not play this selection." }
      }
    }
  }
  Timer {
    id: queueDebounce
    interval: 750
    onTriggered: root.refreshQueue()
  }
  Timer {
    interval: 15000
    running: root.opened && root.queueOpen && root.playbackConnected
    repeat: true
    onTriggered: root.refreshQueue()
  }
  Connections {
    target: root.player
    function onTrackChanged() { if (root.opened && root.queueOpen) queueDebounce.restart() }
  }
  Timer {
    interval: 3000
    running: root.opened && (!root.apiConnected || !root.playbackConnected)
    repeat: true
    onTriggered: root.checkConnection()
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    slotSize: Style.bar.statusSlot
    tooltipText: root.player ? "Spotify — running" : "Spotify — closed"
    opticalSize: Style.space(15)
    iconComponent: Component {
      SpotifyIcon {
        anchors.fill: parent
        tint: root.player ? "#1DB954" : "#EF4444"
      }
    }
    onPressed: function(mouseButton) {
      if (mouseButton === Qt.LeftButton) root.toggle()
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    centerOnBar: true
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(root.queueOpen ? 680 : 400))
    contentHeight: panel.fittedContentHeight(Math.max(content.implicitHeight, root.queueBeside ? Style.space(460) : 0))

    FocusScope {
      id: keyCatcher
      enabled: !root.quittingSpotify
      anchors.fill: parent
      focus: true
      Keys.onEscapePressed: {
        if (root.extraView === "playlist") { root.extraView = "playlists"; keyCatcher.forceActiveFocus() }
        else if (root.extraView !== "") { root.extraView = ""; libraryMenu.reset(); keyCatcher.forceActiveFocus() }
        else root.close()
      }
      Keys.onSpacePressed: root.playPause()
      Keys.onLeftPressed: { if (root.player && root.player.canGoPrevious) root.player.previous() }
      Keys.onRightPressed: { if (root.player && root.player.canGoNext) root.player.next() }

      Flickable {
        id: contentScroll
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: root.queueBeside ? parent.width - queueSidebar.width - Style.space(20) : parent.width
        contentWidth: width
        contentHeight: content.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        interactive: contentHeight > height

      Column {
        id: content
        width: contentScroll.width
        spacing: Style.space(16)

        Item {
          width: parent.width
          height: Style.space(20)
          SpotifyIcon {
            width: Style.space(18)
            height: width
            tint: "#1DB954"
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
          }
          Text {
            text: "SPOTIFY"
            anchors.left: parent.left
            anchors.leftMargin: Style.space(26)
            anchors.verticalCenter: parent.verticalCenter
            color: root.foreground
            font.family: Style.font.family
            font.pixelSize: Style.font.bodySmall
            font.letterSpacing: 1.3
          }
          Row {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: Style.space(6)
            Text {
              anchors.verticalCenter: parent.verticalCenter
              text: root.player ? (root.player.isPlaying ? "Playing" : "Paused") : (backgroundProcess.running ? "Starting…" : "Ready")
              color: root.muted
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
            }
            Button {
              text: "Queue"
              foreground: root.muted
              fontSize: Style.font.caption
              selected: root.queueOpen
              focusable: true
              horizontalPadding: Style.space(5)
              verticalPadding: Style.space(2)
              onClicked: root.queueOpen = !root.queueOpen
            }
          }
        }

        Row {
          width: parent.width
          spacing: Style.space(16)
          Rectangle {
            width: Style.space(88)
            height: width
            color: Style.normalFillFor(root.foreground, Color.accent)
            radius: Style.cornerRadius
            clip: true
            Image {
              id: artwork
              anchors.fill: parent
              source: root.player ? root.player.trackArtUrl : ""
              asynchronous: true
              fillMode: Image.PreserveAspectCrop
              sourceSize.width: 176
              sourceSize.height: 176
            }
            SpotifyIcon {
              anchors.centerIn: parent
              width: Style.space(36)
              height: width
              tint: root.muted
              visible: artwork.status !== Image.Ready
            }
          }
          Column {
            width: parent.width - Style.space(104)
            anchors.verticalCenter: parent.verticalCenter
            spacing: Style.space(5)
            Text {
              width: parent.width
              textFormat: Text.PlainText
              text: root.title
              color: root.foreground
              font.family: Style.font.family
              font.pixelSize: Style.font.heading
              font.bold: true
              maximumLineCount: 2
              wrapMode: Text.Wrap
              elide: Text.ElideRight
            }
            Text {
              width: parent.width
              textFormat: Text.PlainText
              text: root.artist || (root.player ? "Choose a song or playlist" : "Choose a playlist or search for music")
              color: root.muted
              font.family: Style.font.family
              font.pixelSize: Style.font.body
              elide: Text.ElideRight
            }
            Text {
              width: parent.width
              visible: text !== ""
              textFormat: Text.PlainText
              text: root.album
              color: root.muted
              opacity: 0.8
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              elide: Text.ElideRight
            }
          }
        }

        Column {
          width: parent.width
          spacing: Style.space(2)
          visible: root.duration > 0
          PanelSlider {
            id: seek
            width: parent.width
            bar: root.bar
            minimum: 0
            maximum: Math.max(1, root.duration)
            value: root.position
            step: 5
            enabled: root.player && root.player.canSeek
            opacity: enabled ? 1 : 0.5
            onReleased: function(value) { if (root.player && root.player.canSeek) root.player.position = value }
          }
          Item {
            width: parent.width
            height: elapsed.implicitHeight
            Text {
              id: elapsed
              text: root.timeLabel(seek.dragging ? seek.liveValue : root.position)
              color: root.muted
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
            }
            Text {
              anchors.right: parent.right
              text: root.timeLabel(root.duration)
              color: root.muted
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
            }
          }
        }

        Row {
          anchors.horizontalCenter: parent.horizontalCenter
          spacing: Style.space(10)
          Button {
            id: shuffleButton
            anchors.verticalCenter: parent.verticalCenter
            iconText: "\u{f049f}"
            tooltipText: "Shuffle: " + (root.shuffleOn ? "On" : "Off")
              + "\nClick to turn " + (root.shuffleOn ? "off" : "on")
              + ". Smart Shuffle must be set in Spotify."
            Accessible.name: "Shuffle " + (root.shuffleOn ? "on" : "off")
            foreground: root.shuffleOn ? "#1DB954" : root.muted
            iconSize: Style.font.iconLarge
            focusable: true
            enabled: root.player && root.player.canControl && root.player.shuffleSupported
            opacity: enabled ? 1 : 0.3
            onClicked: root.toggleShuffle()
            Rectangle {
              anchors.horizontalCenter: parent.horizontalCenter
              anchors.bottom: parent.bottom
              anchors.bottomMargin: Style.space(2)
              width: Style.space(3)
              height: width
              radius: width / 2
              color: "#1DB954"
              visible: root.shuffleOn
            }
          }
          Button {
            anchors.verticalCenter: parent.verticalCenter
            iconText: "󰒮"
            tooltipText: "Previous"
            foreground: root.foreground
            iconSize: Style.font.iconLarge
            enabled: root.player && root.player.canGoPrevious
            opacity: enabled ? 1 : 0.3
            onClicked: root.player.previous()
          }
          Button {
            anchors.verticalCenter: parent.verticalCenter
            iconText: root.player && root.player.isPlaying ? "󰏤" : "󰐊"
            tooltipText: root.player && root.player.isPlaying ? "Pause" : "Play"
            foreground: root.foreground
            background: Style.selectedFillFor(root.foreground, Color.accent)
            iconSize: Style.font.display
            horizontalPadding: Style.space(18)
            verticalPadding: Style.space(10)
            enabled: !desktopProcess.running && (!root.player || root.player.canTogglePlaying)
            opacity: enabled ? 1 : 0.3
            onClicked: root.playPause()
          }
          Button {
            anchors.verticalCenter: parent.verticalCenter
            iconText: "󰒭"
            tooltipText: "Next"
            foreground: root.foreground
            iconSize: Style.font.iconLarge
            enabled: root.player && root.player.canGoNext
            opacity: enabled ? 1 : 0.3
            onClicked: root.player.next()
          }
          Button {
            id: repeatButton
            anchors.verticalCenter: parent.verticalCenter
            iconText: root.repeatMode === MprisLoopState.Track ? "\u{f0458}" : "\u{f0456}"
            tooltipText: "Repeat: " + root.repeatLabel + "\nClick for "
              + (root.repeatMode === MprisLoopState.None ? "single song"
                : root.repeatMode === MprisLoopState.Track ? "playlist" : "off")
            Accessible.name: "Repeat " + root.repeatLabel
            foreground: root.repeatMode !== MprisLoopState.None ? "#1DB954" : root.muted
            iconSize: Style.font.iconLarge
            focusable: true
            enabled: root.player && root.player.canControl && root.player.loopSupported
            opacity: enabled ? 1 : 0.3
            onClicked: root.cycleRepeat()
            Rectangle {
              anchors.horizontalCenter: parent.horizontalCenter
              anchors.bottom: parent.bottom
              anchors.bottomMargin: Style.space(2)
              width: Style.space(3)
              height: width
              radius: width / 2
              color: "#1DB954"
              visible: root.repeatMode !== MprisLoopState.None
            }
          }
        }

        Row {
          width: parent.width
          spacing: Style.space(8)
          Button {
            id: volumeMuteButton
            anchors.verticalCenter: parent.verticalCenter
            iconText: root.spotifyVolume === 0 ? "\u{f075f}"
              : root.spotifyVolume < 0.5 ? "\u{f0580}" : "\u{f057e}"
            tooltipText: root.spotifyVolume === 0 ? "Unmute Spotify" : "Mute Spotify"
            Accessible.name: tooltipText
            foreground: root.muted
            iconSize: Style.font.iconLarge
            horizontalPadding: Style.space(6)
            focusable: true
            enabled: root.volumeAvailable
            opacity: enabled ? 1 : 0.3
            onClicked: root.toggleMute()
          }
          PanelSlider {
            id: volumeSlider
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - volumeMuteButton.width - volumePercent.width - Style.space(16)
            bar: root.bar
            minimum: 0
            maximum: 100
            step: 5
            integer: true
            value: root.spotifyVolume * 100
            enabled: root.volumeAvailable
            opacity: enabled ? 1 : 0.3
            activeFocusOnTab: true
            Accessible.name: "Spotify volume"
            Keys.onLeftPressed: root.setVolume(value - step)
            Keys.onRightPressed: root.setVolume(value + step)
            Keys.onUpPressed: root.setVolume(value + step)
            Keys.onDownPressed: root.setVolume(value - step)
            onMoved: function(value) { root.setVolume(value) }
            onReleased: function(value) { root.setVolume(value) }
            onRightClicked: root.toggleMute()
          }
          Text {
            id: volumePercent
            anchors.verticalCenter: parent.verticalCenter
            width: Style.space(40)
            text: root.volumeAvailable
              ? Math.round(volumeSlider.dragging ? volumeSlider.liveValue : root.spotifyVolume * 100) + "%"
              : "—"
            horizontalAlignment: Text.AlignRight
            color: root.muted
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
          }
        }

        PanelSeparator { width: parent.width; foreground: root.foreground }

        Row {
          width: parent.width
          spacing: Style.space(6)
          Button {
            width: (parent.width - Style.space(12)) / 3
            text: "Playlists"
            iconText: "󰅀"
            foreground: root.foreground
            selected: root.extraView === "playlists"
            focusable: true
            horizontalPadding: Style.space(6)
            onClicked: root.showView("playlists")
          }
          Button {
            width: (parent.width - Style.space(12)) / 3
            text: "Search"
            iconText: "󰍉"
            foreground: root.foreground
            selected: root.extraView === "search"
            focusable: true
            horizontalPadding: Style.space(6)
            onClicked: root.showView("search")
          }
          Button {
            width: (parent.width - Style.space(12)) / 3
            text: "Open Spotify"
            foreground: root.foreground
            focusable: true
            horizontalPadding: Style.space(6)
            onClicked: root.openApp()
          }
        }

        Item {
          width: parent.width
          height: quitButton.implicitHeight
          Button {
            id: quitButton
            anchors.right: parent.right
            text: root.quittingSpotify ? "Quitting…" : "Quit Spotify"
            iconText: "󰅀"
            foreground: root.muted
            selected: root.extraView === "quit"
            focusable: true
            enabled: !!root.player && !backgroundProcess.running && !desktopProcess.running && !playbackProcess.running && !searchProcess.running && !root.quittingSpotify
            opacity: enabled ? 1 : 0.4
            onClicked: root.showView("quit")
          }
        }

        Column {
          width: parent.width
          spacing: Style.space(8)
          visible: root.extraView === "quit"
          Text {
            text: "Quit Spotify?"
            color: root.foreground
            font.family: Style.font.family
            font.pixelSize: Style.font.body
            font.bold: true
          }
          Text {
            width: parent.width
            text: "Stops music and closes Spotify completely."
            color: root.muted
            font.family: Style.font.family
            font.pixelSize: Style.font.bodySmall
            wrapMode: Text.WordWrap
          }
          Row {
            spacing: Style.space(8)
            Button {
              text: "Cancel"
              foreground: root.foreground
              focusable: true
              onClicked: { root.extraView = ""; keyCatcher.forceActiveFocus() }
            }
            Button {
              text: "Quit Spotify"
              foreground: root.foreground
              bordered: true
              focusable: true
              onClicked: root.confirmQuit()
            }
          }
        }

        PlaylistBrowser {
          id: playlistBrowser
          width: parent.width
          visible: root.extraView === "playlist"
          playlist: root.playlistData
          foreground: root.foreground
          currentUri: root.currentTrackUri
          loading: playlistProcess.running
          busy: playbackProcess.running
          error: root.playlistError
          playbackConnected: root.playbackConnected
          playing: root.player && root.player.isPlaying && root.queueData.context_uri === root.playlistData.uri
          shuffleOn: root.shuffleOn
          shuffleAvailable: root.player && root.player.canControl && root.player.shuffleSupported
          onBackRequested: { root.extraView = "playlists"; keyCatcher.forceActiveFocus() }
          onOpenRequested: root.openPlaylistApp()
          onRefreshRequested: root.loadPlaylist(true)
          onAuthorizeRequested: root.connectAccount()
          onPlayRequested: function(position) { root.playPlaylist(position) }
          onShuffleRequested: root.toggleShuffle()
        }

        LibraryMenu {
          id: libraryMenu
          width: parent.width
          visible: root.extraView === "playlists"
          foreground: root.foreground
          onConnectionChanged: function(connected) { root.apiConnected = connected }
          onChosen: function(playlist) { root.choosePlaylist(playlist) }
          onBackRequested: { root.extraView = ""; keyCatcher.forceActiveFocus() }
        }

        Column {
          width: parent.width
          spacing: Style.space(10)
          visible: root.extraView === "search"
          TextField {
            id: searchField
            width: parent.width
            foreground: root.foreground
            placeholderText: "Songs, artists, albums, playlists"
            onAccepted: root.search()
            Keys.onEscapePressed: { root.extraView = ""; keyCatcher.forceActiveFocus() }
          }
          Row {
            width: parent.width
            spacing: Style.space(8)
            Button {
              text: searchProcess.running ? "Searching…" : (root.apiConnected ? "Search" : "Search in Spotify")
              iconText: "󰍉"
              foreground: root.foreground
              bordered: true
              focusable: true
              enabled: searchField.text.trim() !== "" && !searchProcess.running
              opacity: enabled ? 1 : 0.4
              onClicked: root.search()
            }
            Button {
              text: "Cancel"
              foreground: root.muted
              focusable: true
              onClicked: { root.extraView = ""; keyCatcher.forceActiveFocus() }
            }
          }
          Text {
            width: parent.width
            visible: root.searchError !== "" || !root.apiConnected || (root.searched && root.searchResults.length === 0)
            text: root.searchError || (!root.apiConnected ? "Connect Spotify to see results here." : "No results found. Try another search.")
            color: root.muted
            font.family: Style.font.family
            font.pixelSize: Style.font.bodySmall
            wrapMode: Text.WordWrap
          }
          SearchResults {
            width: parent.width
            visible: root.apiConnected && root.searchResults.length > 0
            items: root.searchResults
            foreground: root.foreground
            onChosen: function(result) { root.choosePlaylist(result) }
          }
        }

        QueuePanel {
          width: parent.width
          height: Style.space(420)
          visible: root.queueOpen && !root.queueBeside
          foreground: root.foreground
          queue: root.queueData
          title: root.title
          artist: root.artist
          cover: root.player ? root.player.trackArtUrl : ""
          currentUri: root.currentTrackUri
          loading: queueProcess.running
          busy: playbackProcess.running
          onPlayRequested: function(track) { root.playQueuedTrack(track) }
          connected: root.playbackConnected
          error: root.playbackError || root.queueError
          onCloseRequested: root.queueOpen = false
          onRefreshRequested: root.refreshQueue()
          onAuthorizeRequested: root.connectAccount()
        }

        Item {
          width: parent.width
          height: connectionButton.implicitHeight
          Text {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            text: root.apiConnected ? "Account connected" : "Connect for playlists & search"
            color: root.muted
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
          }
          Button {
            id: connectionButton
            anchors.right: parent.right
            text: authProcess.running ? "Connecting…" : (root.apiConnected ? "Disconnect" : "Connect Spotify")
            foreground: root.foreground
            fontSize: Style.font.bodySmall
            focusable: true
            enabled: !authProcess.running
            onClicked: { if (root.apiConnected) root.disconnectAccount(); else root.connectAccount() }
          }
        }
        Text {
          width: parent.width
          visible: root.connectionError !== ""
          text: root.connectionError
          color: root.foreground
          font.family: Style.font.family
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap
        }

        Text {
          width: parent.width
          visible: root.playbackError !== "" || (!root.player && backgroundProcess.running)
          text: root.playbackError || "Starting Spotify in the background…"
          horizontalAlignment: Text.AlignHCenter
          color: root.muted
          font.family: Style.font.family
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap
        }
      }
      }
      Rectangle {
        visible: root.queueBeside
        width: Math.max(1, Style.space(1))
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: queueSidebar.left
        anchors.rightMargin: Style.space(10)
        color: root.muted
        opacity: 0.25
      }
      QueuePanel {
        id: queueSidebar
        visible: root.queueBeside
        width: Math.min(Style.space(250), keyCatcher.width * 0.4)
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        foreground: root.foreground
        queue: root.queueData
        title: root.title
        artist: root.artist
        cover: root.player ? root.player.trackArtUrl : ""
        currentUri: root.currentTrackUri
        loading: queueProcess.running
        busy: playbackProcess.running
        onPlayRequested: function(track) { root.playQueuedTrack(track) }
        connected: root.playbackConnected
        error: root.playbackError || root.queueError
        onCloseRequested: root.queueOpen = false
        onRefreshRequested: root.refreshQueue()
        onAuthorizeRequested: root.connectAccount()
      }
    }
  }
}
