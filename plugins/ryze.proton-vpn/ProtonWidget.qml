import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons as Commons
import qs.Ui as Ui

Ui.BarWidget {
    id: root
    moduleName: "ryze.proton-vpn"
    property bool opened: false
    property bool popoutSwitchClosing: false
    property var status: ({running: false, state: "unknown", server: "", can_connect: false, can_disconnect: false})
    property string error: ""
    property string actionError: ""
    property var serverRows: []
    property int serverTotal: 0
    property int serverOffset: 0
    property string serverError: ""
    property string serverNotice: ""
    property string searchQuery: ""
    property int searchOffset: 0
    property int searchGeneration: 0
    property bool searchPending: false
    readonly property string helper: decodeURIComponent(Qt.resolvedUrl("proton_status.py").toString().replace(/^file:\/\//, ""))
    readonly property string stateLabel: status.state === "connected" ? "Connected"
        : status.state === "disconnected" ? "Not connected"
        : status.state === "connecting" ? "Connecting…"
        : status.state === "disconnecting" ? "Disconnecting…" : "Connection status unavailable"
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight

    function refresh() { if (!reader.running) reader.running = true }
    function open() { popoutSwitchClosing = false; opened = true; refresh(); searchServers(browser.query, serverOffset) }
    function close() { opened = false }
    function closeForPopoutSwitch() { popoutSwitchClosing = true; close() }
    function toggle() { if (opened) close(); else open() }
    function action(name, target) {
        if (actionProcess.running || status.picker_pending) return
        actionError = ""
        actionProcess.command = ["python3", "-B", helper, name]
        if (target) actionProcess.command.push(target)
        actionProcess.running = true
        if (name === "open") close()
    }
    function searchServers(query, offset) {
        searchQuery = query
        searchOffset = offset
        searchGeneration++
        serverError = ""
        if (serverProcess.running) { searchPending = true; return }
        startSearch()
    }
    function startSearch() {
        searchPending = false
        serverProcess.requestGeneration = searchGeneration
        serverProcess.command = ["python3", "-B", helper, "search", searchQuery, String(searchOffset)]
        serverProcess.running = true
    }
    Process {
        id: serverProcess
        property int requestGeneration: 0
        stdout: StdioCollector {
            onStreamFinished: {
                if (serverProcess.requestGeneration !== root.searchGeneration) return
                try {
                    var result = JSON.parse(text)
                    root.serverRows = result.ok ? (result.rows || []) : []
                    root.serverTotal = result.ok ? result.total : 0
                    root.serverOffset = result.ok ? result.offset : 0
                    root.serverNotice = result.notice || ""
                    root.serverError = result.ok ? "" : (result.error || "Could not search servers.")
                } catch (e) { root.serverRows = []; root.serverTotal = 0; root.serverError = "Could not read the server list." }
            }
        }
        onExited: if (root.searchPending) Qt.callLater(function() { root.startSearch() })
    }
    Timer {
        interval: root.opened ? 2000 : 5000
        running: true; repeat: true; triggeredOnStart: true
        onTriggered: root.refresh()
    }
    Process {
        id: reader
        command: ["python3", "-B", root.helper, "status"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var result = JSON.parse(text)
                    root.status = result
                    root.error = result.error || ""
                } catch (e) {
                    root.status = {running: false, state: "unknown", server: "", can_connect: false, can_disconnect: false}
                    root.error = "Could not read Proton VPN status."
                }
            }
        }
    }
    Process {
        id: actionProcess
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var result = JSON.parse(text)
                    if (!result.ok) {
                        root.actionError = result.error || "Open Proton VPN to continue."
                        if (!root.opened) Quickshell.execDetached(["notify-send", "-a", "Proton VPN", "Proton VPN", root.actionError])
                    }
                } catch (e) { root.actionError = "Could not complete the Proton VPN action." }
            }
        }
        onExited: root.broadcast("refresh")
    }
    IpcHandler {
        enabled: !!root.bar && root.bar.moduleWidgets(root.moduleName)[0] === root
        target: root.moduleName
        function open(): void { root.open() }
        function close(): void { root.close() }
        function search(query: string): void { root.open(); browser.setQuery(query) }
        function status(): string { return JSON.stringify({opened: root.opened, status: root.status, error: root.error, iconSize: button.opticalSize, slotSize: button.slotSize, query: root.searchQuery, serverCount: root.serverRows.length, serverTotal: root.serverTotal, serverError: root.serverError}) }
    }
    Ui.BarIconButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        slotSize: Commons.Style.bar.statusSlot
        opticalSize: Commons.Style.space(12)
        iconComponent: Component {
            ProtonIcon { appRunning: root.status.running === true; connectionState: root.status.state || "unknown" }
        }
        tooltipText: "Proton VPN — app " + (root.status.running ? "on" : "off") + "\n" + root.stateLabel
        onPressed: function(mouseButton) {
            if (mouseButton === Qt.LeftButton) root.toggle()
            else if (mouseButton === Qt.RightButton) root.action("open")
        }
    }
    Ui.KeyboardPanel {
        id: panel
        anchorItem: button; owner: root; bar: root.bar
        open: root.opened
        focusTarget: browser.keyboardTarget
        contentWidth: fittedContentWidth(Commons.Style.space(480))
        contentHeight: fittedContentHeight(content.implicitHeight)
        Item {
            id: content
            anchors.fill: parent
            implicitHeight: column.implicitHeight + Commons.Style.space(32)
            focus: true
            Keys.onEscapePressed: root.close()
            ColumnLayout {
                id: column
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                anchors.margins: Commons.Style.space(16)
                spacing: Commons.Style.space(12)
                RowLayout {
                    spacing: Commons.Style.space(12)
                    ProtonIcon {
                        Layout.preferredWidth: Commons.Style.space(36)
                        Layout.preferredHeight: Commons.Style.space(36)
                        appRunning: root.status.running === true
                        connectionState: root.status.state || "unknown"
                    }
                    ColumnLayout {
                        spacing: Commons.Style.space(4)
                        Text { text: "Proton VPN"; color: Commons.Color.foreground; font.family: Commons.Style.font.family; font.pixelSize: Commons.Style.font.body; font.bold: true }
                        Text { text: "App " + (root.status.running ? "on" : "off"); color: root.status.running ? "#FFFFFF" : "#8B8D98"; font.family: Commons.Style.font.family; font.pixelSize: Commons.Style.font.bodySmall }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: root.stateLabel + (root.status.server ? " · " + root.status.server : "")
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    color: root.status.state === "connected" ? "#30C88B" : root.status.state === "disconnected" ? "#F25F68" : "#F2BC65"
                    font.family: Commons.Style.font.family; font.pixelSize: Commons.Style.font.body
                }
                Ui.Button {
                    Layout.fillWidth: true
                    text: root.status.can_disconnect ? "Disconnect" : "Quick connect"
                    enabled: !actionProcess.running && !root.status.picker_pending && (root.status.can_disconnect || root.status.can_connect)
                    focusable: true; bordered: true
                    onClicked: root.action(root.status.can_disconnect ? "disconnect" : "connect")
                }
                ServerBrowser {
                    id: browser
                    Layout.fillWidth: true
                    servers: root.serverRows
                    total: root.serverTotal
                    offset: root.serverOffset
                    loading: serverProcess.running || root.searchPending
                    busy: actionProcess.running || root.status.picker_pending === true
                    available: root.status.picker_available === true
                    selectionAllowed: root.status.selection_allowed === true
                    currentServer: root.status.state === "connected" ? root.status.server : ""
                    error: root.serverError
                    notice: root.serverNotice
                    onSearchRequested: function(query, offset) { root.searchServers(query, offset) }
                    onConnectRequested: function(name) { root.action("select", name) }
                }
                Ui.Button {
                    Layout.fillWidth: true
                    text: root.status.running ? "Open Proton VPN / Settings" : "Start Proton VPN"
                    enabled: !actionProcess.running
                    focusable: true; bordered: true
                    onClicked: root.action("open")
                }
                Text {
                    Layout.fillWidth: true
                    text: root.error || root.actionError || root.status.picker_error || "Select a server, then press Connect. Advanced settings remain in the official app."
                    textFormat: Text.PlainText; wrapMode: Text.Wrap
                    color: (root.error || root.actionError || root.status.picker_error) ? "#F25F68" : Commons.Color.foreground
                    font.family: Commons.Style.font.family; font.pixelSize: Commons.Style.font.bodySmall
                }
            }
        }
    }
}
