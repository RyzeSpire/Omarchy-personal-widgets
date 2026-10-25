import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import qs.Commons as Commons
import qs.Ui as Ui

ColumnLayout {
    id: root
    property var servers: []
    property int total: 0
    property int offset: 0
    property bool loading: false
    property bool busy: false
    property bool available: false
    property bool selectionAllowed: false
    property string currentServer: ""
    property string selectedName: ""
    property string error: ""
    property string notice: ""
    property alias query: search.text
    property alias keyboardTarget: search
    spacing: Commons.Style.space(8)
    signal searchRequested(string query, int offset)
    signal connectRequested(string name)
    function setQuery(value) { search.text = value.slice(0, 128) }
    function focusSearch() { search.forceActiveFocus() }
    function refresh() { root.searchRequested(search.text, root.offset) }
    onServersChanged: selectedName = ""
    Timer { id: debounce; interval: 250; onTriggered: root.searchRequested(search.text, 0) }
    RowLayout {
        Layout.fillWidth: true
        Ui.TextField {
            id: search
            Layout.fillWidth: true
            placeholderText: "Country, city or server…"
            maximumLength: 128
            enabled: root.available
            selectByMouse: true
            onTextChanged: { root.selectedName = ""; debounce.restart() }
            onAccepted: { debounce.stop(); root.searchRequested(text, 0) }
        }
        Ui.Button {
            text: "Refresh"; focusable: true
            enabled: root.available && !root.loading
            onClicked: root.refresh()
        }
    }
    Text {
        Layout.fillWidth: true
        text: root.loading ? "Searching…" : !root.available ? "Start Proton VPN to search its servers."
            : root.error || (root.total ? (root.offset + 1) + "–" + (root.offset + root.servers.length) + " of " + root.total + " servers" : "No matching servers")
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
        color: root.error ? "#F25F68" : Commons.Color.foreground
        font.family: Commons.Style.font.family; font.pixelSize: Commons.Style.font.bodySmall
    }
    ListView {
        id: list
        Layout.fillWidth: true
        Layout.preferredHeight: Commons.Style.space(190)
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: root.servers
        spacing: Commons.Style.space(4)
        enabled: root.available && !root.loading
        Controls.ScrollBar.vertical: Controls.ScrollBar { }
        delegate: Ui.Button {
            required property var modelData
            width: list.width - Commons.Style.space(12)
            text: modelData.name + (modelData.name === root.currentServer ? "  ✓ Connected" : "")
                + " · " + modelData.load + "% load\n" + modelData.country
                + (modelData.city ? " · " + modelData.city : "")
                + (modelData.secure_core ? " · Secure Core via " + modelData.entry_country : "")
                + (modelData.tor ? " · Tor" : "") + (modelData.free ? " · Free" : "")
            fontSize: Commons.Style.font.bodySmall
            horizontalPadding: Commons.Style.space(8)
            verticalPadding: Commons.Style.space(6)
            leftAlign: true; focusable: true
            selected: root.selectedName === modelData.name
            onClicked: root.selectedName = modelData.name
        }
    }
    RowLayout {
        Layout.fillWidth: true
        Ui.Button {
            text: "Previous"; focusable: true
            enabled: root.available && !root.loading && root.offset > 0
            onClicked: root.searchRequested(search.text, Math.max(0, root.offset - 50))
        }
        Item { Layout.fillWidth: true }
        Ui.Button {
            text: "Next"; focusable: true
            enabled: root.available && !root.loading && root.offset + root.servers.length < root.total
            onClicked: root.searchRequested(search.text, root.offset + 50)
        }
    }
    Ui.Button {
        Layout.fillWidth: true
        text: root.busy ? "Connection request in progress…" : root.selectedName ? "Connect to " + root.selectedName : "Select a server above"
        enabled: root.available && root.selectionAllowed && !root.busy && !root.loading && !!root.selectedName && root.selectedName !== root.currentServer
        focusable: true; bordered: true
        onClicked: root.connectRequested(root.selectedName)
    }
    Text {
        Layout.fillWidth: true
        visible: !!root.notice
        text: root.notice
        textFormat: Text.PlainText; wrapMode: Text.Wrap
        color: "#F2BC65"
        font.family: Commons.Style.font.family; font.pixelSize: Commons.Style.font.bodySmall
    }
}
