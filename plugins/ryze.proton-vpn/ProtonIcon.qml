import QtQuick
import QtQuick.Effects
import Quickshell

Item {
    id: root
    property bool appRunning: false
    property string connectionState: "unknown"
    readonly property color tint: appRunning ? "#FFFFFF" : "#8B8D98"
    readonly property color lockColor: connectionState === "connected" ? "#30C88B"
        : connectionState === "disconnected" ? "#F25F68"
        : connectionState === "unknown" ? "#8B8D98" : "#F2BC65"
    Image {
        id: logo
        x: 0; y: parent.height * 0.22
        width: parent.width * 0.82; height: parent.height * 0.78
        source: Quickshell.iconPath("proton-vpn-sign")
        sourceSize.width: 64; sourceSize.height: 64
        fillMode: Image.PreserveAspectFit
        visible: false
        layer.enabled: true
    }
    MultiEffect {
        anchors.fill: logo
        source: logo
        colorization: 1.0
        colorizationColor: root.tint
        brightness: root.appRunning ? 0.6 : 0.15
    }
    Canvas {
        id: lock
        x: parent.width * 0.48; y: 0
        width: parent.width * 0.52; height: parent.height * 0.62
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Connections {
            target: root
            function onConnectionStateChanged() { lock.requestPaint() }
        }
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset(); ctx.scale(width / 14, height / 16)
            ctx.fillStyle = root.lockColor; ctx.strokeStyle = root.lockColor
            ctx.lineWidth = 2.3; ctx.lineCap = "round"
            if (root.connectionState === "unknown") {
                ctx.font = "bold 15px sans-serif"; ctx.fillText("?", 3, 14); return
            }
            ctx.beginPath()
            if (root.connectionState === "connected") {
                ctx.moveTo(4, 7); ctx.lineTo(4, 4)
                ctx.bezierCurveTo(4, 0, 11, 0, 11, 4); ctx.lineTo(11, 7)
            } else {
                ctx.moveTo(7, 7); ctx.lineTo(7, 4)
                ctx.bezierCurveTo(7, 0, 13, 0, 13, 4)
            }
            ctx.stroke()
            ctx.fillRect(2, 7, 11, 8)
        }
    }
}
