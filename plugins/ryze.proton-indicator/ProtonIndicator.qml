import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons as Commons
import qs.Ui as Ui

Ui.BarWidget {
    id: root
    moduleName: "ryze.proton-indicator"
    property bool appRunning: false
    property string connectionState: "unknown"
    property string error: ""
    readonly property string helper: decodeURIComponent(Qt.resolvedUrl("proton_indicator.py").toString().replace("file://", ""))
    readonly property string connectionLabel: connectionState === "connected" ? "VPN connected"
        : connectionState === "disconnected" ? "VPN not connected"
        : connectionState === "connecting" ? "VPN connecting…"
        : connectionState === "disconnecting" ? "VPN disconnecting…" : "VPN status unavailable"
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    function refresh() { if (!reader.running) reader.running = true }
    Timer { interval: 5000; running: true; repeat: true; triggeredOnStart: true; onTriggered: root.refresh() }
    Process {
        id: reader
        command: ["python3", "-B", root.helper, "status"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var result = JSON.parse(text)
                    root.appRunning = result.running === true
                    root.connectionState = result.state || "unknown"
                    root.error = result.error || ""
                } catch (e) { root.connectionState = "unknown"; root.error = "Could not read Proton VPN status." }
            }
        }
    }
    Process {
        id: opener
        command: ["python3", "-B", root.helper, "open"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var result = JSON.parse(text)
                    if (!result.ok) Quickshell.execDetached(["notify-send", "-a", "Proton VPN", "Proton VPN", result.error || "Open the official Proton VPN app."])
                } catch (e) {}
            }
        }
        onExited: root.refresh()
    }
    IpcHandler {
        enabled: !!root.bar && root.bar.moduleWidgets(root.moduleName)[0] === root
        target: root.moduleName
        function status(): string { return JSON.stringify({running: root.appRunning, state: root.connectionState, error: root.error, iconSize: button.opticalSize}) }
    }
    Ui.BarIconButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        slotSize: Commons.Style.bar.statusSlot
        opticalSize: Commons.Style.space(12)
        iconComponent: Component { ProtonIcon { appRunning: root.appRunning; connectionState: root.connectionState } }
        tooltipText: "Proton VPN — app " + (root.appRunning ? "on" : "off") + "\n" + root.connectionLabel + "\nClick to open the official app"
        enabled: !opener.running
        onPressed: function(mouseButton) { if ((mouseButton === Qt.LeftButton || mouseButton === Qt.RightButton) && !opener.running) opener.running = true }
    }
}
