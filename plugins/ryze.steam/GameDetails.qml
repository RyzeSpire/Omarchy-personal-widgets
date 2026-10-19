import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as Controls
import qs.Commons as Commons
import qs.Ui as Ui

FocusScope {
    id: root
    property var gameInfo: ({name: "Game details", achievements: {}, friends: {entries: []}})
    property bool loading: false
    property bool friendsLoading: false
    property bool busy: false
    property bool clientAvailable: true
    property string error: ""
    property color foreground: Commons.Color.foreground
    property bool aboutOpen: false
    property bool actionsOpen: false
    property bool achievementsOpen: false
    property bool friendsOpen: false
    property bool installConfirm: false
    readonly property var achievementInfo: gameInfo.achievements || ({})
    readonly property var friendInfo: gameInfo.friends || ({entries: []})
    implicitHeight: Math.min(Commons.Style.space(510), toolbar.implicitHeight + content.implicitHeight + Commons.Style.space(10))
    signal backRequested()
    signal refreshRequested()
    signal playRequested(string appid)
    signal favoriteRequested(string appid, bool enabled)
    signal actionRequested(string appid, string action)
    signal friendsRequested(string appid)
    signal friendChatRequested(string steamid)

    function focusSearch() { root.forceActiveFocus() }
    function openSection(section) {
        if (section === "about") aboutOpen = true
        else if (section === "achievements") achievementsOpen = true
        else if (section === "actions") actionsOpen = true
        else if (section === "friends") {
            friendsOpen = true
            if (!root.loading && !root.friendsLoading && !friendInfo.loaded) root.friendsRequested(gameInfo.appid)
        }
        Qt.callLater(function() { if (section === "friends") scroll.contentY = Math.max(0, scroll.contentHeight - scroll.height) })
    }
    function hours(minutes) { return minutes === null || minutes === undefined ? "Not available" : (minutes / 60).toFixed(1) + " h" }
    function lastPlayed() {
        if (gameInfo.last_played) return new Date(gameInfo.last_played * 1000).toLocaleDateString(Qt.locale(), "d MMM yyyy")
        return gameInfo.playtime_minutes === 0 ? "Never played" : "Not recorded"
    }
    function size(bytes) { return bytes >= 1073741824 ? (bytes / 1073741824).toFixed(1) + " GiB" : Math.round(bytes / 1048576) + " MiB" }
    Keys.onEscapePressed: {
        if (installConfirm) installConfirm = false
        else if (actionsOpen) actionsOpen = false
        else root.backRequested()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Commons.Style.space(10)
        RowLayout {
            id: toolbar
            Layout.fillWidth: true
            Ui.Button {
                text: "‹ Back"
                foreground: root.foreground
                focusable: true
                onClicked: root.backRequested()
            }
            Item { Layout.fillWidth: true }
            Text {
                text: root.loading ? "Loading details…" : root.gameInfo.installed ? "Installed" : "Not installed"
                color: Qt.darker(root.foreground, 1.5)
                font.family: Commons.Style.font.family
                font.pixelSize: Commons.Style.font.caption
            }
            Ui.Button {
                iconText: "\uf021"
                foreground: root.foreground
                focusable: true
                enabled: !root.loading
                tooltipText: "Refresh game information"
                onClicked: root.refreshRequested()
            }
        }
        Flickable {
            id: scroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            contentWidth: width
            contentHeight: content.implicitHeight
            Controls.ScrollBar.vertical: Controls.ScrollBar { policy: Controls.ScrollBar.AsNeeded }
            Column {
                id: content
                width: scroll.width
                spacing: Commons.Style.space(12)
                Rectangle {
                    width: parent.width
                    height: Commons.Style.space(150)
                    color: "#1b2838"
                    clip: true
                    Image {
                        anchors.fill: parent
                        source: root.gameInfo.hero || root.gameInfo.artwork || ""
                        asynchronous: true
                        fillMode: Image.PreserveAspectCrop
                    }
                    Rectangle {
                        anchors.fill: parent
                        gradient: Gradient {
                            GradientStop { position: 0.3; color: "transparent" }
                            GradientStop { position: 1; color: "#DD000000" }
                        }
                    }
                    Image {
                        id: gameLogo
                        anchors.left: parent.left
                        anchors.bottom: parent.bottom
                        anchors.margins: Commons.Style.space(14)
                        width: parent.width * 0.55
                        height: Commons.Style.space(58)
                        source: root.gameInfo.logo || ""
                        fillMode: Image.PreserveAspectFit
                        horizontalAlignment: Image.AlignLeft
                        verticalAlignment: Image.AlignBottom
                        asynchronous: true
                    }
                    Text {
                        visible: gameLogo.status !== Image.Ready
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: Commons.Style.space(14)
                        text: root.gameInfo.name || "Game details"
                        textFormat: Text.PlainText
                        color: "white"
                        font.family: Commons.Style.font.family
                        font.pixelSize: Commons.Style.space(21)
                        font.bold: true
                        wrapMode: Text.Wrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                    }
                }
                RowLayout {
                    width: parent.width
                    Ui.Button {
                        text: root.gameInfo.installed ? "Play" : "Install in Steam"
                        iconText: root.gameInfo.installed ? "\uf04b" : "\uf019"
                        foreground: "#66C0F4"
                        bordered: true
                        focusable: true
                        enabled: !root.busy && root.clientAvailable
                        onClicked: {
                            if (root.gameInfo.installed) root.playRequested(root.gameInfo.appid)
                            else root.installConfirm = !root.installConfirm
                        }
                    }
                    Item { Layout.fillWidth: true }
                    Ui.Button {
                        iconText: "\uf013"
                        selected: root.actionsOpen
                        foreground: root.foreground
                        tooltipText: "Steam actions"
                        focusable: true
                        onClicked: root.actionsOpen = !root.actionsOpen
                    }
                    Ui.Button {
                        iconText: "\uf05a"
                        selected: root.aboutOpen
                        foreground: root.foreground
                        tooltipText: root.aboutOpen ? "Hide game information" : "Show game information"
                        focusable: true
                        onClicked: root.aboutOpen = !root.aboutOpen
                    }
                    Ui.Button {
                        iconText: root.gameInfo.favorite ? "\uf004" : "\uf08a"
                        foreground: root.gameInfo.favorite ? "#E5C07B" : root.foreground
                        tooltipText: root.gameInfo.favorite ? "Unpin from widget favorites" : "Pin to widget favorites"
                        focusable: true
                        enabled: !root.busy
                        onClicked: root.favoriteRequested(root.gameInfo.appid, !root.gameInfo.favorite)
                    }
                }
                Column {
                    width: parent.width
                    visible: root.installConfirm
                    spacing: Commons.Style.space(7)
                    Text {
                        width: parent.width
                        text: "Open Steam’s installation dialog for this game?"
                        color: root.foreground
                        wrapMode: Text.Wrap
                        font.family: Commons.Style.font.family
                        font.pixelSize: Commons.Style.font.bodySmall
                    }
                    Row {
                        spacing: Commons.Style.space(8)
                        Ui.Button { text: "Cancel"; foreground: root.foreground; focusable: true; onClicked: root.installConfirm = false }
                        Ui.Button {
                            text: "Continue in Steam"
                            foreground: "#66C0F4"
                            focusable: true
                            enabled: !root.busy && root.clientAvailable
                            onClicked: root.actionRequested(root.gameInfo.appid, "install")
                        }
                    }
                }
                Flow {
                    width: parent.width
                    visible: root.actionsOpen
                    spacing: Commons.Style.space(5)
                    Repeater {
                        model: [{label: "Open in Steam", action: "steam"}, {label: "Properties (Steam)", action: "properties"},
                            {label: "Store page", action: "store"}, {label: "Community hub", action: "community"}]
                        Ui.Button {
                            required property var modelData
                            text: modelData.label
                            foreground: root.foreground
                            focusable: true
                            enabled: !root.busy && root.clientAvailable
                            fontSize: Commons.Style.font.caption
                            onClicked: root.actionRequested(root.gameInfo.appid, modelData.action)
                        }
                    }
                }
                Row {
                    width: parent.width
                    spacing: Commons.Style.space(8)
                    Repeater {
                        model: [ {label: root.gameInfo.installed ? "INSTALLED SIZE" : "STORAGE (MINIMUM)",
                            value: root.gameInfo.installed ? root.size(root.gameInfo.size || 0) : root.gameInfo.storage_required || "Not available"},
                            {label: "LAST PLAYED", value: root.lastPlayed()}, {label: "PLAY TIME", value: root.hours(root.gameInfo.playtime_minutes)} ]
                        Column {
                            required property var modelData
                            width: (content.width - Commons.Style.space(16)) / 3
                            spacing: Commons.Style.space(4)
                            Text {
                                width: parent.width
                                text: modelData.label
                                color: Qt.darker(root.foreground, 1.6)
                                font.family: Commons.Style.font.family
                                font.pixelSize: Commons.Style.font.caption
                                elide: Text.ElideRight
                            }
                            Text {
                                width: parent.width
                                text: modelData.value
                                color: root.foreground
                                font.family: Commons.Style.font.family
                                font.pixelSize: Commons.Style.font.bodySmall
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
                Text {
                    width: parent.width
                    visible: root.gameInfo.history_source === "local_cache"
                    text: "Cached play history"
                    color: Qt.darker(root.foreground, 1.6)
                    font.family: Commons.Style.font.family
                    font.pixelSize: Commons.Style.font.caption
                }
                Column {
                    width: parent.width
                    visible: root.aboutOpen
                    spacing: Commons.Style.space(9)
                    Text {
                        width: parent.width
                        text: root.gameInfo.description || "A description is not available in the local cache."
                        textFormat: Text.PlainText
                        color: root.foreground
                        wrapMode: Text.Wrap
                        font.family: Commons.Style.font.family
                        font.pixelSize: Commons.Style.font.bodySmall
                    }
                    Text {
                        width: parent.width
                        text: [ (root.gameInfo.developers || []).length ? "Developer: " + root.gameInfo.developers.join(", ") : "",
                            (root.gameInfo.publishers || []).length ? "Publisher: " + root.gameInfo.publishers.join(", ") : "",
                            root.gameInfo.release_date ? "Released: " + root.gameInfo.release_date : "",
                            (root.gameInfo.platforms || []).length ? "Platforms: " + root.gameInfo.platforms.join(", ") : "" ].filter(function(v) { return !!v }).join("\n")
                        textFormat: Text.PlainText
                        color: Qt.darker(root.foreground, 1.35)
                        wrapMode: Text.Wrap
                        font.family: Commons.Style.font.family
                        font.pixelSize: Commons.Style.font.caption
                    }
                    Flow {
                        width: parent.width
                        spacing: Commons.Style.space(5)
                        Repeater {
                            model: root.gameInfo.features || []
                            Rectangle {
                                required property var modelData
                                width: Math.min(content.width, feature.implicitWidth + Commons.Style.space(12))
                                height: feature.implicitHeight + Commons.Style.space(8)
                                radius: Commons.Style.cornerRadius
                                color: "#223146"
                                Text {
                                    id: feature
                                    anchors.centerIn: parent
                                    width: parent.width - Commons.Style.space(12)
                                    text: modelData
                                    textFormat: Text.PlainText
                                    elide: Text.ElideRight
                                    color: "#AFC9DD"
                                    font.family: Commons.Style.font.family
                                    font.pixelSize: Commons.Style.font.caption
                                }
                            }
                        }
                    }
                }
                Ui.Button {
                    width: parent.width
                    text: (root.achievementsOpen ? "− " : "+ ") + "Achievements" + (root.achievementInfo.available ? " · " + root.achievementInfo.unlocked + "/" + root.achievementInfo.total : "")
                    foreground: "#AFC9DD"
                    leftAlign: true
                    focusable: true
                    onClicked: root.achievementsOpen = !root.achievementsOpen
                }
                Column {
                    width: parent.width
                    visible: root.achievementsOpen
                    spacing: Commons.Style.space(8)
                    Text {
                        width: parent.width
                        text: root.achievementInfo.available ? "Unlocked " + root.achievementInfo.unlocked + "/" + root.achievementInfo.total
                            + " (" + (root.achievementInfo.total ? Math.round(100 * root.achievementInfo.unlocked / root.achievementInfo.total) : 0) + "%)"
                            + (root.achievementInfo.source === "local_cache" ? " · cached" : "") : "Achievement progress is not available for this game or profile."
                        color: root.foreground
                        wrapMode: Text.Wrap
                        font.family: Commons.Style.font.family
                        font.pixelSize: Commons.Style.font.bodySmall
                    }
                    Rectangle {
                        width: parent.width
                        height: Commons.Style.space(6)
                        color: "#223146"
                        radius: height / 2
                        visible: !!root.achievementInfo.available
                        Rectangle {
                            width: parent.width * (root.achievementInfo.total ? Math.min(1,root.achievementInfo.unlocked/root.achievementInfo.total) : 0)
                            height: parent.height
                            radius: parent.radius
                            color: "#66C0F4"
                        }
                    }
                    Repeater {
                        model: (root.achievementInfo.items || []).slice(0,3)
                        Row {
                            required property var modelData
                            width: content.width
                            spacing: Commons.Style.space(10)
                            Image {
                                width: Commons.Style.space(34)
                                height: width
                                source: root.achievementsOpen ? modelData.icon : ""
                                fillMode: Image.PreserveAspectFit
                                asynchronous: true
                            }
                            Column {
                                width: parent.width - Commons.Style.space(44)
                                Text {
                                    width: parent.width
                                    text: modelData.name
                                    textFormat: Text.PlainText
                                    elide: Text.ElideRight
                                    color: root.foreground
                                    font.family: Commons.Style.font.family
                                    font.pixelSize: Commons.Style.font.bodySmall
                                }
                                Text {
                                    width: parent.width
                                    text: (modelData.unlocked ? "Unlocked" : "Locked") + (modelData.description ? " · " + modelData.description : "")
                                    textFormat: Text.PlainText
                                    elide: Text.ElideRight
                                    color: Qt.darker(root.foreground,1.5)
                                    font.family: Commons.Style.font.family
                                    font.pixelSize: Commons.Style.font.caption
                                }
                            }
                        }
                    }
                    Ui.Button {
                        text: "View all achievements in Steam"
                        foreground: "#66C0F4"
                        focusable: true
                        enabled: !root.busy && root.clientAvailable
                        onClicked: root.actionRequested(root.gameInfo.appid, "achievements")
                    }
                }
                Ui.Button {
                    width: parent.width
                    text: (root.friendsOpen ? "− " : "+ ") + "Friends who play" + (root.friendInfo.loaded ? " · " + (root.friendInfo.entries || []).length : "")
                    foreground: "#AFC9DD"
                    leftAlign: true
                    focusable: true
                    enabled: !root.loading && !root.friendsLoading
                    onClicked: {
                        root.friendsOpen = !root.friendsOpen
                        if (root.friendsOpen && !root.friendInfo.loaded) root.friendsRequested(root.gameInfo.appid)
                    }
                }
                Column {
                    width: parent.width
                    visible: root.friendsOpen
                    spacing: Commons.Style.space(8)
                    Text {
                        width: parent.width
                        visible: root.friendsLoading || !(root.friendInfo.entries || []).length
                        text: root.friendsLoading ? "Checking visible friend game activity…" : root.friendInfo.loaded
                            ? "No matches found in the available friend game details." : "Expand to check your friends’ visible play history."
                        wrapMode: Text.Wrap
                        color: Qt.darker(root.foreground,1.4)
                        font.family: Commons.Style.font.family
                        font.pixelSize: Commons.Style.font.bodySmall
                    }
                    Repeater {
                        model: root.friendInfo.entries || []
                        RowLayout {
                            required property var modelData
                            width: content.width
                            Image {
                                Layout.preferredWidth: Commons.Style.space(30)
                                Layout.preferredHeight: Commons.Style.space(30)
                                source: modelData.avatar
                                asynchronous: true
                                fillMode: Image.PreserveAspectCrop
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Commons.Style.space(3)
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.name
                                    textFormat: Text.PlainText
                                    elide: Text.ElideRight
                                    color: modelData.activity === "Playing now" ? "#9ECD73" : "#66C0F4"
                                    font.family: Commons.Style.font.family
                                    font.pixelSize: Commons.Style.font.bodySmall
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.activity + (modelData.playtime_minutes !== null && modelData.playtime_minutes !== undefined ? " · " + root.hours(modelData.playtime_minutes) + " total" : "")
                                    color: Qt.darker(root.foreground,1.5)
                                    font.family: Commons.Style.font.family
                                    font.pixelSize: Commons.Style.font.caption
                                }
                            }
                            Ui.Button {
                                iconText: "\uf075"
                                foreground: "#66C0F4"
                                focusable: true
                                enabled: !root.busy && root.clientAvailable
                                tooltipText: "Chat in Steam"
                                onClicked: root.friendChatRequested(modelData.steamid)
                            }
                        }
                    }
                    Text {
                        width: parent.width
                        text: root.friendInfo.notice || ""
                        visible: text.length > 0
                        textFormat: Text.PlainText
                        wrapMode: Text.Wrap
                        color: Qt.darker(root.foreground,1.5)
                        font.family: Commons.Style.font.family
                        font.pixelSize: Commons.Style.font.caption
                    }
                }
                Text {
                    width: parent.width
                    visible: root.error.length > 0
                    text: root.error
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    color: "#EF7777"
                    font.family: Commons.Style.font.family
                    font.pixelSize: Commons.Style.font.bodySmall
                }
            }
        }
    }
}
