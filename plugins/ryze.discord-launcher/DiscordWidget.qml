import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "ryze.discord-launcher"
  readonly property string helperPath: decodeURIComponent(Qt.resolvedUrl("launch_discord.py").toString().replace(/^file:\/\//, ""))
  property bool discordRunning: false
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  function refreshStatus() {
    if (!statusProcess.running) statusProcess.running = true
  }

  Process {
    id: statusProcess
    command: ["python3", "-B", root.helperPath, "status"]
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var result = JSON.parse(text)
          if (result.ok) root.discordRunning = result.running === true
        } catch (e) {}
      }
    }
  }

  Timer {
    interval: 2000
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: root.refreshStatus()
  }

  Process {
    id: launcher
    command: ["python3", "-B", root.helperPath, "launch"]
    onExited: root.refreshStatus()
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var result = JSON.parse(text)
          if (result.ok) root.discordRunning = result.running === true
          else Quickshell.execDetached(["notify-send", "-a", "Discord", "Discord launcher", result.error])
        } catch (e) {
          Quickshell.execDetached(["notify-send", "-a", "Discord", "Discord launcher", "Could not open Discord on workspace 8."])
        }
      }
    }
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "\u{f066f}"
    foreground: root.discordRunning ? "#5865F2" : "#8B8D98"
    slotSize: Style.bar.statusSlot
    tooltipText: launcher.running ? "Opening Discord desktop…"
      : "Discord — " + (root.discordRunning ? "running" : "closed") + "\nOpen desktop app on workspace 8"
    enabled: !launcher.running
    onPressed: function(mouseButton) {
      if (mouseButton === Qt.LeftButton && !launcher.running) launcher.running = true
    }
  }
}
