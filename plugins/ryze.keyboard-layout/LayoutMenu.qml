import QtQuick
import qs.Ui
import qs.Commons

PanelKeyCatcher {
  id: root
  property var options: []
  property int activeIndex: 0
  property int cursorIndex: 0
  property bool busy: false
  property string error: ""
  signal selected(int index)
  implicitHeight: content.implicitHeight

  function resetCursor() {
    const current = options.findIndex(option => option.index === activeIndex)
    cursorIndex = Math.max(0, current)
  }
  function moveCursor(step) {
    if (options.length) cursorIndex = (cursorIndex + step + options.length) % options.length
  }
  onOptionsChanged: resetCursor()
  onActiveIndexChanged: resetCursor()
  onMoveRequested: function(dx, dy) { if (dy) moveCursor(dy) }
  onTabRequested: function(direction) { moveCursor(direction) }
  onActivateRequested: if (!busy && options.length) selected(cursorIndex)

  Column {
    id: content
    width: parent.width
    spacing: Style.spacing.sm
    Text {
      text: "Keyboard layout"
      textFormat: Text.PlainText
      color: Color.foreground
      font.family: Style.font.family
      font.pixelSize: Style.font.body
    }
    Repeater {
      model: root.options
      Button {
        required property var modelData
        required property int index
        width: content.width
        leftAlign: true
        text: modelData.label
        iconText: modelData.index === root.activeIndex ? "\uf00c" : ""
        selected: modelData.index === root.activeIndex
        hasCursor: index === root.cursorIndex
        enabled: !root.busy
        onHovered: function(hovering) { if (hovering) root.cursorIndex = index }
        onClicked: root.selected(index)
      }
    }
    Text {
      width: parent.width
      visible: root.error !== "" || root.options.length === 0
      text: root.error || "No configured layouts are available."
      textFormat: Text.PlainText
      wrapMode: Text.WordWrap
      color: Color.foreground
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
    }
  }
}
