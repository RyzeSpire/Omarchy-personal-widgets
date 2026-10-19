import QtQuick
import QtQuick.Layouts
import qs.Commons as Commons
import qs.Ui as Ui

ColumnLayout {
    id: root
    property string menu: ""
    property bool busy: false
    property bool clientAvailable: true
    property bool installedOnly: false
    property bool includeSoftware: false
    property bool recentFirst: false
    property color foreground: Commons.Color.foreground
    spacing: Commons.Style.space(8)
    signal shortcutRequested(string target)
    signal storeSearchRequested(string query)
    signal installedOnlyRequested(bool value)
    signal softwareRequested(bool value)
    signal recentRequested(bool value)
    signal refreshRequested()
    function focusSearch() {
        if (root.menu === "store") storeQuery.forceActiveFocus()
        else root.forceActiveFocus()
    }

    Text {
        Layout.fillWidth: true
        text: root.menu === "friends" ? "Friends & chat" : root.menu === "store" ? "Steam Store"
            : root.menu === "settings" ? "Library settings" : "Big Picture"
        color: "#AFC9DD"
        font.family: Commons.Style.font.family
        font.pixelSize: Commons.Style.font.body
        font.bold: true
    }
    Text {
        Layout.fillWidth: true
        visible: root.menu === "friends" || root.menu === "bigpicture" || root.menu === "store"
        text: root.menu === "friends" ? "Live friends, status and chat are available in Steam."
            : root.menu === "store" ? "Choose a search here; results open in Steam."
            : "Enter Steam’s controller-friendly interface."
        wrapMode: Text.Wrap
        color: Qt.darker(root.foreground, 1.4)
        font.family: Commons.Style.font.family
        font.pixelSize: Commons.Style.font.bodySmall
    }
    RowLayout {
        visible: root.menu === "store"
        Layout.fillWidth: true
        Ui.TextField {
            id: storeQuery
            Layout.fillWidth: true
            placeholderText: "Search the Steam Store…"
            foreground: root.foreground
            maximumLength: 200
            selectByMouse: true
            onAccepted: if (text.trim() && !root.busy && root.clientAvailable) root.storeSearchRequested(text.trim())
        }
        Ui.Button {
            text: "Search"
            foreground: "#66C0F4"
            focusable: true
            enabled: !!storeQuery.text.trim() && !root.busy && root.clientAvailable
            onClicked: root.storeSearchRequested(storeQuery.text.trim())
        }
    }
    ColumnLayout {
        visible: root.menu === "settings"
        Layout.fillWidth: true
        spacing: Commons.Style.space(6)
        Repeater {
            model: [ {label: "Installed games only", value: root.installedOnly, key: "installed"},
                {label: "Include software", value: root.includeSoftware, key: "software"},
                {label: "Sort by last played", value: root.recentFirst, key: "recent"} ]
            Ui.Button {
                required property var modelData
                Layout.fillWidth: true
                text: (modelData.value ? "✓ " : "○ ") + modelData.label
                selected: modelData.value
                leftAlign: true
                foreground: root.foreground
                focusable: true
                onClicked: {
                    if (modelData.key === "installed") root.installedOnlyRequested(!modelData.value)
                    else if (modelData.key === "software") root.softwareRequested(!modelData.value)
                    else root.recentRequested(!modelData.value)
                }
            }
        }
        Ui.Button {
            Layout.fillWidth: true
            text: "Refresh library & collections"
            foreground: root.foreground
            focusable: true
            onClicked: root.refreshRequested()
        }
    }
    Ui.Button {
        Layout.fillWidth: true
        text: root.menu === "friends" ? "Open friends & chat" : root.menu === "store" ? "Open full store"
            : root.menu === "settings" ? "Open Steam settings" : "Enter Big Picture"
        foreground: "#66C0F4"
        bordered: true
        focusable: true
        enabled: !root.busy && root.clientAvailable
        onClicked: root.shortcutRequested(root.menu)
    }
}
