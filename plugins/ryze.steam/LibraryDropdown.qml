import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as Controls
import qs.Commons as Commons
import qs.Ui as Ui

FocusScope {
    id: root
    property var catalog: []
    property var collections: []
    property bool installedOnly: false
    property bool includeSoftware: false
    property bool recentFirst: false
    property bool busy: false
    property bool clientAvailable: true
    property color foreground: Commons.Color.foreground
    property string notice: ""
    property var expanded: ({})
    property bool typeMenuOpen: false
    readonly property var rows: buildRows()
    implicitHeight: filters.implicitHeight + (types.visible ? types.implicitHeight + Commons.Style.space(8) : 0)
        + search.implicitHeight + Math.min(Commons.Style.space(360), Math.max(Commons.Style.space(110), rows.reduce(function(sum, row) { return sum + Commons.Style.space(row.header ? 38 : 36) }, 0)))
        + footnote.implicitHeight + Commons.Style.space(8) * 3
    signal launchRequested(string appid)
    signal detailsRequested(string appid)
    signal installedOnlyRequested(bool value)
    signal softwareRequested(bool value)
    signal recentRequested(bool value)
    signal backRequested()
    Keys.onEscapePressed: {
        if (typeMenuOpen) typeMenuOpen = false
        else if (search.text.length) search.text = ""
        else root.backRequested()
    }

    function focusSearch() { search.forceActiveFocus() }

    function toggleGroup(id) {
        var next = Object.assign({}, expanded)
        next[id] = !expanded[id]
        expanded = next
    }
    function buildRows() {
        var query = search.text.trim().toLocaleLowerCase()
        var lookup = {}
        catalog.forEach(function(game) {
            if ((!installedOnly || game.installed) && (includeSoftware || game.type !== "application")) lookup[game.appid] = game
        })
        var result = []
        var groups = collections.slice()
        var pins = catalog.filter(function(game) { return game.favorite }).map(function(game) { return game.appid })
        if (pins.length) groups.unshift({id: "widget:pins", name: "Widget pins", appids: pins})
        groups.forEach(function(group) {
            var all = group.appids.map(function(id) { return lookup[id] }).filter(function(game) { return !!game })
            var matches = all.filter(function(game) { return game.name.toLocaleLowerCase().indexOf(query) !== -1 })
            if (query && !matches.length) return
            matches.sort(function(a, b) {
                if (recentFirst && a.last_played !== b.last_played) return b.last_played - a.last_played
                return a.name.localeCompare(b.name)
            })
            var isOpen = !!expanded[group.id] || !!query
            result.push({header: true, id: group.id, name: group.name, count: all.length, matching: matches.length, expanded: isOpen})
            if (isOpen) matches.forEach(function(game) { result.push({header: false, game: game}) })
        })
        return result
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Commons.Style.space(8)
        RowLayout {
            id: filters
            Layout.fillWidth: true
            Ui.Button {
                text: root.includeSoftware ? "Games & software ▾" : "Games ▾"
                foreground: "#AFC9DD"
                bordered: true
                focusable: true
                fontSize: Commons.Style.font.bodySmall
                onClicked: root.typeMenuOpen = !root.typeMenuOpen
            }
            Item { Layout.fillWidth: true }
            Ui.Button {
                iconText: "\uf019"
                selected: root.installedOnly
                foreground: root.foreground
                tooltipText: root.installedOnly ? "Show all cached library games" : "Show installed games only"
                focusable: true
                onClicked: root.installedOnlyRequested(!root.installedOnly)
            }
            Ui.Button {
                iconText: root.recentFirst ? "\uf017" : "\uf15d"
                foreground: root.foreground
                tooltipText: root.recentFirst ? "Sorted by last played · switch to A–Z" : "Sorted A–Z · switch to last played"
                focusable: true
                onClicked: root.recentRequested(!root.recentFirst)
            }
        }
        RowLayout {
            id: types
            visible: root.typeMenuOpen
            Layout.fillWidth: true
            Ui.Button {
                text: "Games"
                selected: !root.includeSoftware
                foreground: root.foreground
                focusable: true
                onClicked: { root.softwareRequested(false); root.typeMenuOpen = false }
            }
            Ui.Button {
                text: "Games & software"
                selected: root.includeSoftware
                foreground: root.foreground
                focusable: true
                onClicked: { root.softwareRequested(true); root.typeMenuOpen = false }
            }
        }
        Ui.TextField {
            id: search
            Layout.fillWidth: true
            foreground: root.foreground
            placeholderText: "Search your Steam collections…"
            selectByMouse: true
            Keys.onEscapePressed: {
                if (text.length) text = ""
                else root.backRequested()
            }
        }
        ListView {
            id: library
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: Commons.Style.space(90)
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: root.rows
            Controls.ScrollBar.vertical: Controls.ScrollBar { policy: Controls.ScrollBar.AsNeeded }
            delegate: Item {
                id: row
                required property var modelData
                width: library.width
                height: Commons.Style.space(modelData.header ? 38 : 36)
                clip: true
                Ui.Button {
                    anchors.fill: parent
                    visible: row.modelData.header
                    text: (row.modelData.expanded ? "− " : "+ ") + (row.modelData.name || "").toUpperCase()
                        + " (" + (search.text.trim() ? row.modelData.matching + "/" : "") + row.modelData.count + ")"
                    foreground: "#AFC9DD"
                    selected: !!row.modelData.expanded
                    accent: "#66C0F4"
                    leftAlign: true
                    focusable: true
                    fontSize: Commons.Style.font.body
                    horizontalPadding: Commons.Style.space(5)
                    tooltipText: row.modelData.name || ""
                    onClicked: root.toggleGroup(row.modelData.id)
                }
                Item {
                    anchors.fill: parent
                    visible: !row.modelData.header
                    Image {
                        id: icon
                        x: Commons.Style.space(12)
                        anchors.verticalCenter: parent.verticalCenter
                        width: Commons.Style.space(26)
                        height: width
                        source: row.modelData.game ? (row.modelData.game.icon || row.modelData.game.artwork || "") : ""
                        asynchronous: true
                        fillMode: Image.PreserveAspectCrop
                        Text {
                            anchors.centerIn: parent
                            visible: icon.status !== Image.Ready
                            text: "\uf1b6"
                            color: "#66C0F4"
                            font.family: Commons.Style.font.family
                            font.pixelSize: Commons.Style.font.icon
                        }
                    }
                    Text {
                        anchors.left: icon.right
                        anchors.leftMargin: Commons.Style.space(9)
                        anchors.right: actions.left
                        anchors.rightMargin: Commons.Style.space(5)
                        anchors.verticalCenter: parent.verticalCenter
                        text: row.modelData.game ? row.modelData.game.name : ""
                        textFormat: Text.PlainText
                        color: row.modelData.game && row.modelData.game.installed ? root.foreground : Qt.darker(root.foreground, 1.25)
                        font.family: Commons.Style.font.family
                        font.pixelSize: Commons.Style.font.bodySmall
                        elide: Text.ElideRight
                    }
                    Row {
                        id: actions
                        anchors.right: parent.right
                        anchors.rightMargin: Commons.Style.space(3)
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: Commons.Style.space(3)
                        Ui.Button {
                            text: "View"
                            foreground: "#66C0F4"
                            fontSize: Commons.Style.font.caption
                            verticalPadding: Commons.Style.space(3)
                            focusable: true
                            enabled: !root.busy
                            tooltipText: row.modelData.game ? "View game information: " + row.modelData.game.name : ""
                            onClicked: if (row.modelData.game) root.detailsRequested(row.modelData.game.appid)
                        }
                        Ui.Button {
                            visible: !!row.modelData.game && row.modelData.game.installed
                            iconText: "\uf04b"
                            foreground: "#66C0F4"
                            verticalPadding: Commons.Style.space(3)
                            focusable: true
                            enabled: !root.busy && root.clientAvailable
                            tooltipText: row.modelData.game ? "Play " + row.modelData.game.name : ""
                            onClicked: if (row.modelData.game) root.launchRequested(row.modelData.game.appid)
                        }
                    }
                }
            }
            Text {
                visible: library.count === 0
                anchors.centerIn: parent
                width: parent.width - Commons.Style.space(20)
                text: search.text.trim() ? "No matching games in these collections." : "No Steam collections are cached yet.\nYour installed games are on the main view."
                color: Qt.darker(root.foreground, 1.5)
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                font.family: Commons.Style.font.family
                font.pixelSize: Commons.Style.font.bodySmall
            }
        }
        Text {
            id: footnote
            Layout.fillWidth: true
            text: root.notice || "Uncategorized shows locally known titles."
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
            color: Qt.darker(root.foreground, 1.6)
            font.family: Commons.Style.font.family
            font.pixelSize: Commons.Style.font.caption
        }
    }
}
