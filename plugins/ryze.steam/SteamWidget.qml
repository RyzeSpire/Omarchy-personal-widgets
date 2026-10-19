import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import qs.Commons as Commons
import qs.Ui as Ui

Ui.BarWidget {
    id: root
    moduleName: "ryze.steam"
    property bool opened: false
    property bool popoutSwitchClosing: false
    property bool steamRunning: false
    property bool clientAvailable: true
    property bool steamFound: false
    property var games: []
    property var catalog: []
    property var collections: []
    property string collectionsNotice: ""
    property string error: ""
    property string warning: ""
    property bool refreshPending: false
    property var friendsData: ({configured: false, profile: {}, friends: [], error: ""})
    property int friendsGeneration: 0
    readonly property string friendsHelper: decodeURIComponent(Qt.resolvedUrl("steam_friends.py").toString().replace(/^file:\/\//, ""))
    readonly property string helper: decodeURIComponent(Qt.resolvedUrl("steam_backend.py").toString().replace(/^file:\/\//, ""))
    readonly property string gameHelper: decodeURIComponent(Qt.resolvedUrl("steam_game_info.py").toString().replace(/^file:\/\//, ""))
    readonly property color foreground: bar ? bar.foreground : Commons.Color.foreground
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight

    function suppressReveal(value) {
        if (bar && typeof bar.setCenterHoverRevealSuppressed === "function") bar.setCenterHoverRevealSuppressed(value)
    }
    function open() {
        popoutSwitchClosing = false
        opened = true
        refreshStatus()
        refreshLibrary()
        if (content.selectedAppid) gameController.load(content.selectedAppid, false)
        if (content.activeMenu === "friends") refreshFriends(false)
        Qt.callLater(function() { if (root.opened) { root.suppressReveal(true); content.focusCurrentView() } })
    }
    function close() { content.clearPrivateFields(); opened = false; suppressReveal(false) }
    function toggle() { if (opened) close(); else open() }
    function closeForPopoutSwitch() { popoutSwitchClosing = true; close() }
    function refreshStatus() { if (!statusProcess.running) statusProcess.running = true }
    function refreshLibrary() {
        if (libraryProcess.running) { refreshPending = true; return }
        refreshPending = false
        libraryProcess.running = true
    }
    function action(args, closeOnSuccess) {
        if (actionProcess.running) return
        error = ""
        actionProcess.closeOnSuccess = closeOnSuccess
        actionProcess.command = ["python3", "-B", root.helper].concat(args)
        actionProcess.running = true
        if (["open", "details", "store-search", "chat"].indexOf(args[0]) !== -1) root.close()
    }
    function refreshFriends(fresh) {
        if (friendsProcess.running || friendsConfigProcess.running) return
        friendsProcess.requestGeneration = friendsGeneration
        friendsProcess.command = ["python3", "-B", friendsHelper, "refresh"]
        if (fresh) friendsProcess.command.push("fresh")
        friendsProcess.running = true
    }
    function configureFriends(apiKey) {
        if (friendsConfigProcess.running) return
        friendsGeneration++
        gameController.invalidate()
        content.closeDetails()
        friendsProcess.running = false
        friendsData = Object.assign({}, friendsData, {error: ""})
        friendsConfigProcess.secret = JSON.stringify({api_key: apiKey})
        friendsConfigProcess.command = ["python3", "-B", friendsHelper, "configure"]
        friendsConfigProcess.disconnecting = false
        friendsConfigProcess.running = true
    }
    function disconnectFriends() {
        if (friendsConfigProcess.running) return
        friendsGeneration++
        gameController.invalidate()
        content.closeDetails()
        friendsProcess.running = false
        friendsConfigProcess.secret = ""
        friendsConfigProcess.command = ["python3", "-B", friendsHelper, "disconnect"]
        friendsConfigProcess.disconnecting = true
        friendsConfigProcess.running = true
    }
    function openFriendChat(steamid) {
        if (actionProcess.running) return
        error = ""
        actionProcess.closeOnSuccess = true
        actionProcess.command = ["python3", "-B", friendsHelper, "chat", steamid]
        actionProcess.running = true
        root.close()
    }
    Timer {
        interval: 30000
        running: root.opened && content.activeMenu === "friends"
        repeat: true
        onTriggered: root.refreshFriends(false)
    }
    Process {
        id: friendsProcess
        property int requestGeneration: 0
        stdout: StdioCollector {
            onStreamFinished: {
                if (friendsProcess.requestGeneration !== root.friendsGeneration) return
                try {
                    var result = JSON.parse(text)
                    if (result.ok) root.friendsData = result
                    else root.friendsData = Object.assign({}, root.friendsData, {error: result.error || "Could not load Steam friends.", stale: true})
                } catch (e) { root.friendsData = Object.assign({}, root.friendsData, {error: "Could not read the friends response.", stale: true}) }
            }
        }
    }
    Process {
        id: friendsConfigProcess
        property string secret: ""
        property bool disconnecting: false
        stdinEnabled: true
        onStarted: {
            if (secret) write(secret + "\n")
            secret = ""
        }
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var result = JSON.parse(text)
                    if (result.ok) {
                        root.friendsData = friendsConfigProcess.disconnecting
                            ? ({configured: false, profile: {}, friends: [], error: "", updated_at: 0})
                            : Object.assign({}, root.friendsData, {configured: true, error: ""})
                        Qt.callLater(function() { root.refreshFriends(true) })
                    } else root.friendsData = Object.assign({}, root.friendsData, {error: result.error || "Could not connect Steam friends."})
                } catch (e) { root.friendsData = Object.assign({}, root.friendsData, {error: "Could not read the friends setup response."}) }
            }
        }
    }
    function focusedInstance() {
        var items = root.bar ? root.bar.moduleWidgets(root.moduleName) : [root]
        var monitor = Hyprland.focusedMonitor
        var name = monitor ? monitor.name : ""
        for (var i = 0; i < items.length; i++) {
            if (items[i].screenName() === name) return items[i]
        }
        return items.length ? items[0] : root
    }
    function screenName() { return panel.screen ? panel.screen.name : "" }
    function openGame(appid) {
        if (!/^[1-9][0-9]{0,9}$/.test(appid)) return
        root.open()
        content.openDetails(appid)
    }
    function showGameSection(section) { content.openGameSection(section) }
    function runGameAction(appid, action) {
        if (actionProcess.running) return
        error = ""
        actionProcess.closeOnSuccess = true
        actionProcess.command = ["python3", "-B", gameHelper, "action", appid, action]
        actionProcess.running = true
        root.close()
    }
    GameInfoController {
        id: gameController
        helperPath: root.gameHelper
        selectedAppid: content.selectedAppid
        previewGames: root.catalog
    }
    function showMenu(name) {
        if (["library", "friends", "store", "settings", "bigpicture"].indexOf(name) === -1) return
        content.closeDetails()
        content.activeMenu = name
        root.open()
    }
    function describe() {
        return JSON.stringify({opened: opened, menu: content.activeMenu,
            game: content.selectedAppid, gameLoading: gameController.loading, gameError: gameController.error,
            configured: !!friendsData.configured, friends: (friendsData.friends || []).length,
            error: friendsData.error || "", refreshing: friendsProcess.running,
            screen: panel.screen ? panel.screen.name : "",
            x: panel.cardOrigin.x, y: panel.cardOrigin.y,
            width: panel.contentWidth, height: panel.contentHeight})
    }
    IpcHandler {
        enabled: !!root.bar && root.bar.moduleWidgets(root.moduleName)[0] === root
        target: root.moduleName
        function menu(name: string): bool {
            if (["library", "friends", "store", "settings", "bigpicture"].indexOf(name) === -1) return false
            var widget = root.focusedInstance()
            if (!widget) return false
            widget.showMenu(name)
            return true
        }
        function game(appid: string): bool {
            if (!/^[1-9][0-9]{0,9}$/.test(appid)) return false
            root.focusedInstance().openGame(appid)
            return true
        }
        function gameSection(section: string): bool {
            if (["about", "achievements", "friends", "actions"].indexOf(section) === -1) return false
            root.focusedInstance().showGameSection(section)
            return true
        }
        function status(): string {
            var widget = root.focusedInstance()
            return widget ? widget.describe() : "{}"
        }
        function refreshFriends(): void { root.broadcast("refreshFriends") }
    }
    Component.onDestruction: suppressReveal(false)

    Timer {
        interval: 3000
        repeat: true
        running: true
        triggeredOnStart: true
        onTriggered: root.refreshStatus()
    }
    Timer {
        interval: 15000
        repeat: true
        running: root.opened
        onTriggered: root.refreshLibrary()
    }
    Process {
        id: statusProcess
        command: ["python3", "-B", root.helper, "status"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var result = JSON.parse(text)
                    if (result.ok) {
                        root.steamRunning = result.running
                        root.clientAvailable = result.client_available
                    }
                } catch (e) {}
            }
        }
    }
    Process {
        id: libraryProcess
        command: ["python3", "-B", root.helper, "library"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var result = JSON.parse(text)
                    if (result.ok) {
                        if (!root.refreshPending) root.games = result.games
                        if (!root.refreshPending) {
                            root.catalog = result.catalog || result.games
                            root.collections = result.collections || []
                            root.collectionsNotice = result.collections_notice || ""
                        }
                        root.steamFound = result.steam_found
                        root.clientAvailable = result.client_available
                        root.warning = result.warnings.join("\n")
                    } else root.error = result.error || "Could not read the Steam library."
                } catch (e) { root.error = "Could not read the Steam library response." }
            }
        }
        onExited: {
            if (root.refreshPending) Qt.callLater(function() { root.refreshLibrary() })
        }
    }
    Process {
        id: actionProcess
        property bool closeOnSuccess: false
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var result = JSON.parse(text)
                    if (result.ok) {
                        if (result.appid !== undefined) {
                            gameController.setFavorite(result.appid, result.favorite)
                            root.games = root.games.map(function(game) {
                                if (game.appid !== result.appid) return game
                                var copy = Object.assign({}, game)
                                copy.favorite = result.favorite
                                return copy
                            })
                            root.refreshLibrary()
                        }
                        if (actionProcess.closeOnSuccess) root.close()
                        root.refreshStatus()
                    } else {
                        root.error = result.error || "Steam did not accept this action."
                        if (!root.opened) Quickshell.execDetached(["notify-send", "-a", "Steam", "Steam widget", root.error])
                    }
                } catch (e) { root.error = "Could not read the Steam action response." }
            }
        }
    }
    Ui.BarIconButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: "\uf1b6"
        foreground: root.steamRunning ? "#66C0F4" : "#8B8D98"
        slotSize: Commons.Style.bar.statusSlot
        tooltipText: "Steam — " + (root.steamRunning ? "running" : "closed") + "\nBrowse installed games"
        onPressed: function(mouseButton) { if (mouseButton === Qt.LeftButton) root.toggle() }
    }
    Ui.KeyboardPanel {
        id: panel
        anchorItem: button
        owner: root
        bar: root.bar
        open: root.opened
        centerOnBar: true
        focusTarget: content.keyboardTarget
        contentWidth: panel.fittedContentWidth(Commons.Style.space(content.selectedAppid ? 600 : 440))
        contentHeight: panel.fittedContentHeight(content.implicitHeight)
        SteamPanel {
            id: content
            anchors.fill: parent
            games: root.games
            catalog: root.catalog
            collections: root.collections
            collectionsNotice: root.collectionsNotice
            gameInfo: gameController.gameInfo
            gameLoading: gameController.loading
            gameFriendsLoading: gameController.friendsLoading
            gameError: gameController.error
            friendsData: root.friendsData
            friendsRefreshing: friendsProcess.running
            friendsConnecting: friendsConfigProcess.running
            steamRunning: root.steamRunning
            steamFound: root.steamFound
            clientAvailable: root.clientAvailable
            refreshing: libraryProcess.running
            busy: actionProcess.running
            error: root.error
            warning: root.warning
            foreground: root.foreground
            onRefreshRequested: { root.error = ""; root.refreshLibrary() }
            onLaunchRequested: function(appid) { root.action(["launch", appid], true) }
            onFavoriteRequested: function(appid, enabled) { root.action(["favorite", appid, enabled ? "on" : "off"], false) }
            onGameInfoRequested: function(appid, fresh) { gameController.load(appid, fresh) }
            onGameFriendsRequested: function(appid) { gameController.loadFriends(appid) }
            onGameActionRequested: function(appid, action) { root.runGameAction(appid, action) }
            onStoreSearchRequested: function(query) { root.action(["store-search", query], true) }
            onShortcutRequested: function(target) { root.action(["open", target], true) }
            onFriendsRefreshRequested: function(fresh) { root.refreshFriends(fresh) }
            onFriendsConnectRequested: function(apiKey) { root.configureFriends(apiKey) }
            onFriendsDisconnectRequested: root.disconnectFriends()
            onFriendChatRequested: function(steamid) { root.openFriendChat(steamid) }
            onCloseRequested: root.close()
        }
    }
}
