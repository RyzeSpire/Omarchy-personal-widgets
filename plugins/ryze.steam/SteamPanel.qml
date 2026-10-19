import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as Controls
import qs.Commons as Commons
import qs.Ui as Ui

FocusScope {
    id: root
    property var games: []
    property bool steamRunning: false
    property bool steamFound: false
    property bool clientAvailable: true
    property bool refreshing: false
    property bool busy: false
    property string error: ""
    property string warning: ""
    property var catalog: []
    property var collections: []
    property string collectionsNotice: ""
    property var friendsData: ({configured: false, profile: {}, friends: [], error: ""})
    property bool friendsRefreshing: false
    property bool friendsConnecting: false
    property string activeMenu: ""
    onActiveMenuChanged: if (activeMenu === "friends") root.friendsRefreshRequested(false)
    property bool installedOnly: false
    property bool includeSoftware: false
    property bool recentFirst: false
    property bool favoritesOnly: false
    property string selectedAppid: ""
    property var gameInfo: ({})
    property bool gameLoading: false
    property bool gameFriendsLoading: false
    property string gameError: ""
    readonly property Item keyboardTarget: selectedAppid && detailsLoader.item ? detailsLoader.item : activeMenu && menuLoader.item ? menuLoader.item : root
    property color foreground: Commons.Color.foreground
    readonly property var filteredGames: games.filter(function(game) {
        return (!root.favoritesOnly || game.favorite) && game.name.toLocaleLowerCase().indexOf(search.text.trim().toLocaleLowerCase()) !== -1
    })
    readonly property int favoriteCount: games.filter(function(game) { return game.favorite }).length
    readonly property real listHeight: Commons.Style.space(Math.min(312, Math.max(80, filteredGames.length * 112 - 8)))
    implicitHeight: header.implicitHeight + shortcuts.implicitHeight + launchButton.implicitHeight
        + (selectedAppid ? (detailsLoader.item ? detailsLoader.item.implicitHeight : Commons.Style.space(400)) : activeMenu ? (menuLoader.item ? menuLoader.item.implicitHeight : Commons.Style.space(140))
            : search.implicitHeight + tabs.implicitHeight + listHeight)
        + (problem.visible ? problem.implicitHeight + Commons.Style.space(12) : 0)
        + Commons.Style.space(12) * (activeMenu || selectedAppid ? 3 : 5)
    signal refreshRequested()
    signal launchRequested(string appid)
    signal favoriteRequested(string appid, bool enabled)
    signal shortcutRequested(string target)
    signal gameInfoRequested(string appid, bool fresh)
    signal gameFriendsRequested(string appid)
    signal gameActionRequested(string appid, string action)
    signal storeSearchRequested(string query)
    signal friendsRefreshRequested(bool fresh)
    signal friendsConnectRequested(string apiKey)
    signal friendsDisconnectRequested()
    signal friendChatRequested(string steamid)
    signal closeRequested()
    focus: true
    Keys.onEscapePressed: {
        if (selectedAppid) closeDetails()
        else if (activeMenu) activeMenu = ""
        else root.closeRequested()
    }
    function selectMenu(target) {
        if (selectedAppid) { selectedAppid = ""; activeMenu = target }
        else activeMenu = activeMenu === target ? "" : target
        Qt.callLater(root.focusCurrentView)
    }

    function openDetails(appid) {
        selectedAppid = appid
        root.gameInfoRequested(appid, false)
        Qt.callLater(root.focusCurrentView)
    }
    function openGameSection(section) {
        if (detailsLoader.item) detailsLoader.item.openSection(section)
    }
    function closeDetails() { selectedAppid = ""; Qt.callLater(root.focusCurrentView) }
    function clearPrivateFields() {
        if (menuLoader.item && typeof menuLoader.item.clearKey === "function") menuLoader.item.clearKey()
    }
    function focusCurrentView() {
        if (selectedAppid && detailsLoader.item) detailsLoader.item.forceActiveFocus()
        else if (menuLoader.item && typeof menuLoader.item.focusSearch === "function") menuLoader.item.focusSearch()
        else root.forceActiveFocus()
    }

    Component {
        id: detailsComponent
        GameDetails {
            gameInfo: root.gameInfo
            loading: root.gameLoading
            friendsLoading: root.gameFriendsLoading
            busy: root.busy
            clientAvailable: root.clientAvailable
            foreground: root.foreground
            error: root.gameError
            onBackRequested: root.closeDetails()
            onRefreshRequested: root.gameInfoRequested(root.selectedAppid, true)
            onPlayRequested: function(appid) { root.launchRequested(appid) }
            onFavoriteRequested: function(appid, enabled) { root.favoriteRequested(appid, enabled) }
            onActionRequested: function(appid, action) { root.gameActionRequested(appid, action) }
            onFriendsRequested: function(appid) { root.gameFriendsRequested(appid) }
            onFriendChatRequested: function(steamid) { root.friendChatRequested(steamid) }
        }
    }
    Component {
        id: libraryComponent
        LibraryDropdown {
            catalog: root.catalog
            collections: root.collections
            notice: root.collectionsNotice
            installedOnly: root.installedOnly
            includeSoftware: root.includeSoftware
            recentFirst: root.recentFirst
            busy: root.busy
            clientAvailable: root.clientAvailable
            foreground: root.foreground
            onLaunchRequested: function(appid) { root.launchRequested(appid) }
            onDetailsRequested: function(appid) { root.openDetails(appid) }
            onInstalledOnlyRequested: function(value) { root.installedOnly = value }
            onSoftwareRequested: function(value) { root.includeSoftware = value }
            onRecentRequested: function(value) { root.recentFirst = value }
            onBackRequested: root.activeMenu = ""
        }
    }
    Component {
        id: friendsComponent
        FriendsDropdown {
            friendsData: root.friendsData
            catalog: root.catalog
            refreshing: root.friendsRefreshing
            connecting: root.friendsConnecting
            busy: root.busy
            clientAvailable: root.clientAvailable
            foreground: root.foreground
            onRefreshRequested: function(fresh) { root.friendsRefreshRequested(fresh) }
            onConnectRequested: function(apiKey) { root.friendsConnectRequested(apiKey) }
            onDisconnectRequested: root.friendsDisconnectRequested()
            onChatRequested: function(steamid) { root.friendChatRequested(steamid) }
            onShortcutRequested: function(target) { root.shortcutRequested(target) }
            onBackRequested: root.activeMenu = ""
        }
    }
    Component {
        id: clientComponent
        ClientDropdown {
            menu: root.activeMenu
            installedOnly: root.installedOnly
            includeSoftware: root.includeSoftware
            recentFirst: root.recentFirst
            busy: root.busy
            clientAvailable: root.clientAvailable
            foreground: root.foreground
            onShortcutRequested: function(target) { root.shortcutRequested(target) }
            onStoreSearchRequested: function(query) { root.storeSearchRequested(query) }
            onInstalledOnlyRequested: function(value) { root.installedOnly = value }
            onSoftwareRequested: function(value) { root.includeSoftware = value }
            onRecentRequested: function(value) { root.recentFirst = value }
            onRefreshRequested: root.refreshRequested()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Commons.Style.space(12)
        RowLayout {
            id: header
            Layout.fillWidth: true
            Text {
                text: "\uf1b6"
                color: "#66C0F4"
                font.family: Commons.Style.font.family
                font.pixelSize: Commons.Style.font.icon
            }
            Text {
                text: "STEAM"
                color: root.foreground
                font.family: Commons.Style.font.family
                font.pixelSize: Commons.Style.font.bodySmall
                font.letterSpacing: 1.3
            }
            Item { Layout.fillWidth: true }
            Text {
                text: root.steamRunning ? "Running" : "Closed"
                color: root.steamRunning ? "#66C0F4" : Qt.darker(root.foreground, 1.5)
                font.family: Commons.Style.font.family
                font.pixelSize: Commons.Style.font.caption
            }
            Ui.Button {
                text: "\uf021"
                tooltipText: "Refresh installed games"
                focusable: true
                enabled: !root.refreshing
                onClicked: root.refreshRequested()
            }
        }
        Flow {
            id: shortcuts
            Layout.fillWidth: true
            spacing: Commons.Style.space(4)
            Repeater {
                model: [ {label: "Library", target: "library"}, {label: "Friends", target: "friends"},
                    {label: "Store", target: "store"}, {label: "Settings", target: "settings"},
                    {label: "Big Picture", target: "bigpicture"} ]
                Ui.Button {
                    required property var modelData
                    text: modelData.label
                    fontSize: Commons.Style.font.caption
                    horizontalPadding: Commons.Style.space(6)
                    foreground: Qt.darker(root.foreground, 1.3)
                    focusable: true
                    selected: root.activeMenu === modelData.target
                    onClicked: root.selectMenu(modelData.target)
                }
            }
        }
        Ui.TextField {
            id: search
            visible: root.activeMenu === "" && !root.selectedAppid
            Layout.fillWidth: true
            placeholderText: "Search installed games…"
            foreground: root.foreground
            selectByMouse: true
            Keys.onEscapePressed: {
                if (text.length) text = ""
                else root.closeRequested()
            }
        }
        RowLayout {
            id: tabs
            visible: root.activeMenu === "" && !root.selectedAppid
            Layout.fillWidth: true
            spacing: Commons.Style.space(6)
            Ui.Button {
                text: "All games · " + root.games.length
                selected: !root.favoritesOnly
                foreground: root.foreground
                focusable: true
                onClicked: root.favoritesOnly = false
            }
            Ui.Button {
                text: "Favorites · " + root.favoriteCount
                selected: root.favoritesOnly
                foreground: root.foreground
                focusable: true
                onClicked: root.favoritesOnly = true
            }
            Item { Layout.fillWidth: true }
        }
        ListView {
            id: list
            visible: root.activeMenu === "" && !root.selectedAppid
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: Commons.Style.space(70)
            Layout.preferredHeight: root.listHeight
            model: root.filteredGames
            spacing: Commons.Style.space(8)
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            Controls.ScrollBar.vertical: Controls.ScrollBar { policy: Controls.ScrollBar.AsNeeded }
            delegate: GameCard {
                required property var modelData
                width: list.width
                game: modelData
                busy: root.busy
                clientAvailable: root.clientAvailable
                foreground: root.foreground
                onLaunchRequested: function(appid) { root.launchRequested(appid) }
                onDetailsRequested: function(appid) { root.openDetails(appid) }
                onFavoriteRequested: function(appid, enabled) { root.favoriteRequested(appid, enabled) }
            }
            Text {
                anchors.centerIn: parent
                width: parent.width - Commons.Style.space(20)
                visible: list.count === 0
                text: root.refreshing ? "Reading your Steam library…" : !root.steamFound
                    ? "No local Steam library found.\nInstall Steam and a game to get started."
                    : search.text.trim() ? "No matching games."
                    : root.favoritesOnly ? "No favorites yet.\nUse ☆ to pin a game here."
                    : "No installed games found."
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                color: Qt.darker(root.foreground, 1.5)
                font.family: Commons.Style.font.family
                font.pixelSize: Commons.Style.font.bodySmall
            }
        }
        Loader {
            id: menuLoader
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: active ? Commons.Style.space(90) : 0
            active: root.activeMenu !== ""
            visible: active && !root.selectedAppid
            sourceComponent: root.activeMenu === "library" ? libraryComponent : root.activeMenu === "friends" ? friendsComponent : clientComponent
        }
        Loader {
            id: detailsLoader
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: active ? Commons.Style.space(100) : 0
            active: root.selectedAppid !== ""
            visible: active
            sourceComponent: detailsComponent
        }
        Text {
            id: problem
            Layout.fillWidth: true
            visible: text.length > 0
            text: root.error || (!root.clientAvailable ? "Steam is missing from PATH." : root.warning)
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
            color: root.error ? "#EF7777" : Qt.darker(root.foreground, 1.5)
            font.family: Commons.Style.font.family
            font.pixelSize: Commons.Style.font.caption
        }
        Ui.Button {
            id: launchButton
            Layout.fillWidth: true
            text: "Open Steam"
            foreground: "#66C0F4"
            bordered: true
            focusable: true
            enabled: !root.busy && root.clientAvailable
            onClicked: root.shortcutRequested("library")
        }

    }
}
