import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons as Commons
import qs.Ui as Ui

Ui.BarWidget {
    id: root
    moduleName: "ryze.codex-launcher"
    readonly property string helperPath: decodeURIComponent(Qt.resolvedUrl("launch_codex.py").toString().replace(/^file:\/\//, ""))
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight

    Process {
        id: launcher
        command: ["python3", "-B", root.helperPath]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var result = JSON.parse(text)
                    if (!result.ok) Quickshell.execDetached(["notify-send", "-a", "Codex", "Codex launcher", result.error])
                } catch (e) {
                    Quickshell.execDetached(["notify-send", "-a", "Codex", "Codex launcher", "Could not open Codex on workspace 7."])
                }
            }
        }
    }

    Ui.BarIconButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: "\uf120"
        foreground: root.bar ? root.bar.foreground : Commons.Color.foreground
        slotSize: Commons.Style.bar.statusSlot
        tooltipText: launcher.running ? "Opening Codex…" : "Codex — resume a chat\nOpen on workspace 7"
        enabled: !launcher.running
        onPressed: function(mouseButton) {
            if (mouseButton === Qt.LeftButton && !launcher.running) launcher.running = true
        }
    }
}
