import QtQuick
import Quickshell.Io

Item {
    id: root
    required property string helperPath
    property string selectedAppid: ""
    property var previewGames: []
    property var gameInfo: ({})
    property string error: ""
    property int generation: 0
    property bool fullReceived: false
    property var favoriteOverrides: ({})
    readonly property bool loading: fullProcess.running
    readonly property bool friendsLoading: friendsProcess.running
    visible: false

    function load(appid, fresh) {
        generation++
        localProcess.running = false
        fullProcess.running = false
        friendsProcess.running = false
        error = ""
        fullReceived = false
        favoriteOverrides = ({})
        var preview = previewGames.find(function(item) { return item.appid === appid }) || ({appid: appid, name: "Game details"})
        gameInfo = Object.assign({}, preview, {achievements: {}, friends: {loaded: false, entries: []}})
        localProcess.requestGeneration = generation
        localProcess.appid = appid
        localProcess.command = ["python3", "-B", helperPath, "local", appid]
        localProcess.command = localProcess.command.concat(["--request-tag", String(generation)])
        localProcess.running = true
        fullProcess.requestGeneration = generation
        fullProcess.appid = appid
        fullProcess.command = ["python3", "-B", helperPath, "info", appid]
        if (fresh) fullProcess.command.push("fresh")
        fullProcess.command = fullProcess.command.concat(["--request-tag", String(generation)])
        fullProcess.running = true
    }
    function receive(info) {
        if (Object.prototype.hasOwnProperty.call(favoriteOverrides, info.appid)) info.favorite = favoriteOverrides[info.appid]
        gameInfo = info
    }
    function setFavorite(appid, enabled) {
        var next = Object.assign({}, favoriteOverrides)
        next[appid] = enabled
        favoriteOverrides = next
        if (gameInfo.appid === appid) gameInfo = Object.assign({}, gameInfo, {favorite: enabled})
    }
    function loadFriends(appid) {
        if (friendsProcess.running || loading) return
        friendsProcess.requestGeneration = generation
        friendsProcess.appid = appid
        friendsProcess.command = ["python3", "-B", helperPath, "friends", appid]
        friendsProcess.command = friendsProcess.command.concat(["--request-tag", String(generation)])
        friendsProcess.running = true
    }
    function invalidate() {
        generation++
        localProcess.running = false
        fullProcess.running = false
        friendsProcess.running = false
        gameInfo = ({})
    }
    Process {
        id: localProcess
        property int requestGeneration: 0
        property string appid: ""
        stdout: StdioCollector {
            onStreamFinished: {
                if (localProcess.requestGeneration !== root.generation || localProcess.appid !== root.selectedAppid || root.fullReceived) return
                try {
                    if (!text.trim()) return
                    var result = JSON.parse(text)
                    if (result.request_tag !== root.generation) return
                    if (result.info && result.info.appid !== root.selectedAppid) return
                    if (result.ok) root.receive(result.info)
                } catch (e) {}
            }
        }
    }
    Process {
        id: fullProcess
        property int requestGeneration: 0
        property string appid: ""
        stdout: StdioCollector {
            onStreamFinished: {
                if (fullProcess.requestGeneration !== root.generation || fullProcess.appid !== root.selectedAppid) return
                try {
                    if (!text.trim()) return
                    var result = JSON.parse(text)
                    if (result.request_tag !== root.generation) return
                    if (result.info && result.info.appid !== root.selectedAppid) return
                    if (result.ok) { root.error = ""; root.fullReceived = true; root.receive(result.info) }
                    else root.error = result.error || "Could not load game information."
                } catch (e) {}
            }
        }
    }
    Process {
        id: friendsProcess
        property int requestGeneration: 0
        property string appid: ""
        stdout: StdioCollector {
            onStreamFinished: {
                if (friendsProcess.requestGeneration !== root.generation || friendsProcess.appid !== root.selectedAppid) return
                try {
                    if (!text.trim()) return
                    var result = JSON.parse(text)
                    if (result.request_tag !== root.generation) return
                    if (result.info && result.info.appid !== root.selectedAppid) return
                    if (result.ok) root.gameInfo = Object.assign({}, root.gameInfo, {friends: result.friends})
                    else root.error = result.error || "Could not load friends’ game activity."
                } catch (e) {}
            }
        }
    }
}
