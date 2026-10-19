import QtQuick

Canvas {
  id: root
  property color tint: "white"
  onTintChanged: requestPaint()
  onWidthChanged: requestPaint()
  onHeightChanged: requestPaint()
  onPaint: {
    var ctx = getContext("2d")
    ctx.reset()
    var size = Math.min(width, height)
    ctx.translate((width - size) / 2, (height - size) / 2)
    ctx.scale(size / 24, size / 24)
    ctx.fillStyle = tint
    ctx.beginPath()
    ctx.arc(12, 12, 11, 0, Math.PI * 2)
    ctx.fill()
    ctx.globalCompositeOperation = "destination-out"
    ctx.lineCap = "round"
    var curves = [[5.3, 8.6, 11, 6.8, 16.3, 7.5, 19, 9.1, 2.1],
                  [6.1, 12.1, 10.7, 10.7, 15.1, 11.2, 17.9, 12.9, 1.8],
                  [6.8, 15.4, 10.5, 14.4, 13.8, 14.8, 16.8, 16.2, 1.5]]
    for (var i = 0; i < curves.length; i++) {
      var c = curves[i]
      ctx.lineWidth = c[8]
      ctx.beginPath()
      ctx.moveTo(c[0], c[1])
      ctx.bezierCurveTo(c[2], c[3], c[4], c[5], c[6], c[7])
      ctx.stroke()
    }
  }
}
