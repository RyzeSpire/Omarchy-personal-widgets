import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as Controls
import Quickshell
import qs.Commons as Commons
import qs.Ui as Ui

FocusScope {
    id: root
    property var friendsData: ({configured: false, profile: {}, friends: [], error: ""})
    property var catalog: []
    property bool refreshing: false
    property bool connecting: false
    property bool busy: false
    property bool clientAvailable: true
    property color foreground: Commons.Color.foreground
    property bool setupOpen: false
    property bool accountOpen: false
    property bool confirmDisconnect: false
    property var collapsed: ({offline: true, unknown: true})
    readonly property bool showSetup: !friendsData.configured || setupOpen
    readonly property var profile: friendsData.profile || ({})
    readonly property var rows: buildRows()
    readonly property string connectionError: friendsData.error || ""
    readonly property real desiredListHeight: Commons.Style.space(Math.min(320, Math.max(90,
        rows.reduce(function(sum, row) { return sum + (row.header ? 30 : 62) }, 0))))
    implicitHeight: identity.implicitHeight + Commons.Style.space(10)
        + (accountActions.visible ? accountActions.implicitHeight + Commons.Style.space(8) : 0)
        + (disconnectPrompt.visible ? disconnectPrompt.implicitHeight + Commons.Style.space(8) : 0)
        + (showSetup ? setup.implicitHeight : search.implicitHeight + desiredListHeight + updated.implicitHeight + chatButton.implicitHeight + Commons.Style.space(8) * 3)
        + (problem.visible ? problem.implicitHeight + Commons.Style.space(8) : 0)
    signal refreshRequested(bool fresh)
    signal connectRequested(string apiKey)
    signal disconnectRequested()
    signal chatRequested(string steamid)
    signal shortcutRequested(string target)
    signal backRequested()

    function clearKey() { keyField.text = "" }
    function focusSearch() {
        if (root.showSetup) keyField.forceActiveFocus()
        else search.forceActiveFocus()
    }
    function groupColor(group) {
        if (root.friendsData.stale) return "#8B8D98"
        return group === "in_game" ? "#9ECD73" : group === "online" ? "#66C0F4" : "#8B8D98"
    }
    function toggleGroup(group) {
        var next = Object.assign({}, collapsed)
        next[group] = !collapsed[group]
        collapsed = next
    }
    function buildRows() {
        if (!(friendsData.friends || []).length) return []
        var query = search.text.trim().toLocaleLowerCase()
        var people = (friendsData.friends || []).filter(function(friend) {
            return (friend.name + " " + friend.game).toLocaleLowerCase().indexOf(query) !== -1
        })
        var result = []
        var groups = [{id: "in_game", label: "In Game"}, {id: "online", label: "Online Friends"},
            {id: "offline", label: "Offline Friends"}, {id: "unknown", label: "Status unavailable"}]
        groups.forEach(function(group) {
            var members = people.filter(function(friend) { return friend.group === group.id })
            if (!members.length && (query || group.id === "unknown")) return
            var isOpen = !collapsed[group.id] || !!query
            result.push({header: true, group: group.id, label: group.label, count: members.length, expanded: isOpen})
            if (isOpen) members.forEach(function(friend) { result.push({header: false, friend: friend}) })
        })
        return result
    }
    function submitKey() {
        var key = keyField.text.trim()
        if (root.connecting || !/^[a-fA-F0-9]{32}$/.test(key)) return
        root.connectRequested(key)
        keyField.text = ""
        setupOpen = false
        accountOpen = false
    }
    Keys.onEscapePressed: {
        if (confirmDisconnect) confirmDisconnect = false
        else if (setupOpen || accountOpen) { setupOpen = false; accountOpen = false }
        else if (search.text.length) search.text = ""
        else root.backRequested()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Commons.Style.space(8)
        RowLayout {
            id: identity
            Layout.fillWidth: true
            spacing: Commons.Style.space(12)
            Rectangle {
                Layout.preferredWidth: Commons.Style.space(48)
                Layout.preferredHeight: Commons.Style.space(48)
                radius: Commons.Style.cornerRadius
                color: "#1b2838"
                border.width: 1
                border.color: root.groupColor(root.profile.group)
                Image {
                    id: ownAvatar
                    anchors.fill: parent
                    anchors.margins: Commons.Style.space(3)
                    source: root.profile.avatar || ""
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                }
                Text {
                    anchors.centerIn: parent
                    visible: ownAvatar.status !== Image.Ready
                    text: "\uf007"
                    color: "#66C0F4"
                    font.family: Commons.Style.font.family
                    font.pixelSize: Commons.Style.font.icon
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Commons.Style.space(4)
                Text {
                    Layout.fillWidth: true
                    text: root.profile.name || "Steam Friends"
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    color: root.foreground
                    font.family: Commons.Style.font.family
                    font.pixelSize: Commons.Style.font.body
                    font.bold: true
                }
                Text {
                    Layout.fillWidth: true
                    text: root.friendsData.configured ? (root.friendsData.stale ? "Last known status" : (root.profile.game || root.profile.status || "Steam Friends"))
                        : "Connect your friends list"
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    color: root.friendsData.configured ? root.groupColor(root.profile.group) : Qt.darker(root.foreground, 1.4)
                    font.family: Commons.Style.font.family
                    font.pixelSize: Commons.Style.font.caption
                }
            }
            Ui.Button {
                text: "\uf021"
                tooltipText: "Refresh friends"
                foreground: root.foreground
                focusable: true
                enabled: !root.refreshing && !root.connecting
                onClicked: root.refreshRequested(true)
            }
            Ui.Button {
                text: "\uf013"
                tooltipText: "Friends account setup"
                foreground: root.foreground
                focusable: true
                enabled: !root.connecting
                onClicked: {
                    if (!root.friendsData.configured) { root.setupOpen = true; Qt.callLater(root.focusSearch) }
                    else root.accountOpen = !root.accountOpen
                }
            }
        }
        RowLayout {
            id: accountActions
            Layout.fillWidth: true
            visible: root.accountOpen && !!root.friendsData.configured
            Ui.Button {
                text: root.setupOpen ? "Cancel setup" : "Change API key"
                foreground: root.foreground
                focusable: true
                enabled: !root.connecting
                onClicked: { root.setupOpen = !root.setupOpen; if (root.setupOpen) Qt.callLater(root.focusSearch) }
            }
            Ui.Button {
                text: "Disconnect"
                foreground: "#EF7777"
                focusable: true
                enabled: !root.connecting
                tooltipText: "Remove this widget’s saved API key and friends cache"
                onClicked: root.confirmDisconnect = true
            }
        }
        ColumnLayout {
            id: disconnectPrompt
            Layout.fillWidth: true
            visible: root.confirmDisconnect
            Text {
                Layout.fillWidth: true
                text: "Remove this widget’s API key and cached friends?"
                wrapMode: Text.Wrap
                color: root.foreground
                font.family: Commons.Style.font.family
                font.pixelSize: Commons.Style.font.bodySmall
            }
            RowLayout {
                Ui.Button { text: "Cancel"; foreground: root.foreground; focusable: true; onClicked: root.confirmDisconnect = false }
                Ui.Button {
                    text: "Disconnect"
                    foreground: "#EF7777"
                    focusable: true
                    onClicked: { root.disconnectRequested(); root.confirmDisconnect = false; root.accountOpen = false; root.setupOpen = false }
                }
            }
        }
        ColumnLayout {
            id: setup
            visible: root.showSetup
            Layout.fillWidth: true
            spacing: Commons.Style.space(10)
            Text {
                Layout.fillWidth: true
                text: "See your friends, online status and current games here. Create a Steam Web API key, then paste it below."
                wrapMode: Text.Wrap
                color: Qt.darker(root.foreground, 1.3)
                font.family: Commons.Style.font.family
                font.pixelSize: Commons.Style.font.bodySmall
            }
            Ui.TextField {
                id: keyField
                Layout.fillWidth: true
                placeholderText: "Steam Web API key"
                password: true
                maximumLength: 64
                selectByMouse: true
                foreground: root.foreground
                enabled: !root.connecting
                onAccepted: root.submitKey()
                Keys.onEscapePressed: { text = ""; root.backRequested() }
            }
            RowLayout {
                Layout.fillWidth: true
                Ui.Button {
                    text: "Get a key"
                    foreground: root.foreground
                    focusable: true
                    onClicked: Quickshell.execDetached(["xdg-open", "https://steamcommunity.com/dev/apikey"])
                }
                Item { Layout.fillWidth: true }
                Ui.Button {
                    text: root.connecting ? "Connecting…" : "Connect"
                    foreground: "#66C0F4"
                    bordered: true
                    focusable: true
                    enabled: !root.connecting && /^[a-fA-F0-9]{32}$/.test(keyField.text.trim())
                    onClicked: root.submitKey()
                }
            }
            Text {
                Layout.fillWidth: true
                text: "Domain: localhost. The key is saved privately on this computer."
                wrapMode: Text.Wrap
                color: Qt.darker(root.foreground, 1.6)
                font.family: Commons.Style.font.family
                font.pixelSize: Commons.Style.font.caption
            }
        }
        Ui.TextField {
            id: search
            visible: !root.showSetup
            Layout.fillWidth: true
            placeholderText: "Search friends or games…"
            foreground: root.foreground
            selectByMouse: true
            Keys.onEscapePressed: {
                if (text.length) text = ""
                else root.backRequested()
            }
        }
        ListView {
            id: friendList
            visible: !root.showSetup
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: Commons.Style.space(80)
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: root.rows
            Controls.ScrollBar.vertical: Controls.ScrollBar { policy: Controls.ScrollBar.AsNeeded }
            delegate: Item {
                id: row
                required property var modelData
                width: friendList.width
                height: Commons.Style.space(modelData.header ? 30 : 62)
                Ui.Button {
                    visible: row.modelData.header
                    anchors.fill: parent
                    text: (row.modelData.expanded ? "− " : "+ ") + (row.modelData.label || "") + " (" + (row.modelData.count || 0) + ")"
                    foreground: "#AFC9DD"
                    leftAlign: true
                    horizontalPadding: Commons.Style.space(4)
                    fontSize: Commons.Style.font.bodySmall
                    focusable: true
                    onClicked: root.toggleGroup(row.modelData.group)
                }
                Rectangle {
                    visible: !row.modelData.header
                    anchors.fill: parent
                    anchors.margins: Commons.Style.space(2)
                    radius: Commons.Style.cornerRadius
                    color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.035)
                    Rectangle {
                        id: avatarFrame
                        x: Commons.Style.space(8)
                        anchors.verticalCenter: parent.verticalCenter
                        width: Commons.Style.space(40)
                        height: width
                        color: "#1b2838"
                        radius: Commons.Style.cornerRadius
                        border.width: 1
                        border.color: root.groupColor(row.modelData.friend ? row.modelData.friend.group : "unknown")
                        Image {
                            id: avatar
                            anchors.fill: parent
                            anchors.margins: Commons.Style.space(2)
                            source: row.modelData.friend ? row.modelData.friend.avatar : ""
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                        }
                        Text {
                            visible: avatar.status !== Image.Ready
                            anchors.centerIn: parent
                            text: "\uf007"
                            color: "#8B8D98"
                            font.family: Commons.Style.font.family
                            font.pixelSize: Commons.Style.font.icon
                        }
                    }
                    Column {
                        anchors.left: avatarFrame.right
                        anchors.leftMargin: Commons.Style.space(10)
                        anchors.right: chat.left
                        anchors.rightMargin: Commons.Style.space(8)
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: Commons.Style.space(4)
                        Text {
                            width: parent.width
                            text: row.modelData.friend ? row.modelData.friend.name : ""
                            textFormat: Text.PlainText
                            elide: Text.ElideRight
                            color: root.groupColor(row.modelData.friend ? row.modelData.friend.group : "unknown")
                            font.family: Commons.Style.font.family
                            font.pixelSize: Commons.Style.font.body
                        }
                        Text {
                            width: parent.width
                            text: row.modelData.friend ? (row.modelData.friend.game || row.modelData.friend.status) : ""
                            textFormat: Text.PlainText
                            elide: Text.ElideRight
                            color: Qt.darker(root.foreground, 1.45)
                            font.family: Commons.Style.font.family
                            font.pixelSize: Commons.Style.font.caption
                        }
                    }
                    Ui.Button {
                        id: chat
                        anchors.right: parent.right
                        anchors.rightMargin: Commons.Style.space(6)
                        anchors.verticalCenter: parent.verticalCenter
                        iconText: "\uf075"
                        foreground: "#66C0F4"
                        tooltipText: row.modelData.friend ? "Chat in Steam with " + row.modelData.friend.name : ""
                        focusable: true
                        enabled: !root.busy && root.clientAvailable
                        onClicked: if (row.modelData.friend) root.chatRequested(row.modelData.friend.steamid)
                    }
                }
            }
            Text {
                anchors.centerIn: parent
                width: parent.width - Commons.Style.space(20)
                visible: !(root.friendsData.friends || []).length || friendList.count === 0
                text: root.refreshing ? "Refreshing friends…" : root.connectionError ? "Your friends could not be loaded."
                    : search.text.trim() ? "No matching friends." : "Your Steam friends list is empty."
                color: Qt.darker(root.foreground, 1.5)
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                font.family: Commons.Style.font.family
                font.pixelSize: Commons.Style.font.bodySmall
            }
        }
        Text {
            id: updated
            Layout.fillWidth: true
            visible: !root.showSetup
            text: root.refreshing ? "Refreshing…" : root.friendsData.stale ? "Last known status · refresh failed"
                : root.friendsData.updated_at ? "Updated " + new Date(root.friendsData.updated_at * 1000).toLocaleTimeString(Qt.locale(), "h:mm AP")
                : "Status follows Steam profile visibility."
            color: Qt.darker(root.foreground, 1.6)
            font.family: Commons.Style.font.family
            font.pixelSize: Commons.Style.font.caption
        }
        Text {
            id: problem
            Layout.fillWidth: true
            visible: text.length > 0
            text: root.connectionError
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
            color: "#EF7777"
            font.family: Commons.Style.font.family
            font.pixelSize: Commons.Style.font.caption
        }
        Ui.Button {
            id: chatButton
            Layout.fillWidth: true
            visible: !root.showSetup
            text: "Open friends & chat in Steam"
            foreground: "#66C0F4"
            bordered: true
            focusable: true
            enabled: !root.busy && root.clientAvailable
            onClicked: root.shortcutRequested("friends")
        }
    }
}
