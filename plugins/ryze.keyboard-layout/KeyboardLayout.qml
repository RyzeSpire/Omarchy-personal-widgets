import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import qs.Ui
import qs.Commons
import "KeyboardLayoutModel.js" as KeyboardLayoutModel

BarWidget {
  id: root
  moduleName: "ryze.keyboard-layout"


  property bool opened: false
  property bool popoutSwitchClosing: false
  property var typedDevices: []
  property var currentKeyboard: null
  property var layoutCatalog: ({})
  readonly property var layoutOptions: KeyboardLayoutModel.configuredLayouts(currentKeyboard, layoutCatalog)
  readonly property bool switching: switchProc.running
  property var switchQueue: []
  property string switchError: ""

  function screenName() { return panel.screen ? panel.screen.name : "" }
  function focusedInstance() {
    const items = bar ? bar.moduleWidgets(moduleName) : [root]
    const monitor = Hyprland.focusedMonitor
    return items.find(item => monitor && item.screenName() === monitor.name) || items[0] || root
  }
  function open() {
    switchError = ""
    opened = true
    refresh()
    menu.resetCursor()
  }
  function close() { opened = false }
  function closeForPopoutSwitch() { popoutSwitchClosing = true; close() }
  function choose() {
    const widget = focusedInstance()
    broadcast("close")
    widget.popoutSwitchClosing = false
    widget.open()
  }
  function selectLayout(index) {
    if (!Number.isInteger(index) || index < 0 || index >= layoutOptions.length || switchProc.running) return false
    const targets = KeyboardLayoutModel.selectionTargets(typedDevices, layoutOptions[index])
    if (!targets.length) return false
    switchError = ""
    switchQueue = targets
    switchNext()
    return true
  }
  function switchNext() {
    if (!switchQueue.length) {
      broadcast("refresh")
      close()
      return
    }
    const target = switchQueue[0]
    switchQueue = switchQueue.slice(1)
    switchProc.command = ["hyprctl", "switchxkblayout", target.name, String(target.index)]
    switchProc.running = true
  }

  IpcHandler {
    enabled: !!root.bar && root.bar.moduleWidgets(root.moduleName)[0] === root
    target: "ryze.keyboard-layout"
    function choose(): void { root.choose() }
    function close(): void { root.broadcast("close") }
    function select(index: int): bool { return root.focusedInstance().selectLayout(index) }
    function status(): string {
      const widget = root.focusedInstance()
      return JSON.stringify({opened: widget.opened, screen: widget.screenName(),
        activeIndex: widget.activeLayoutIndex, options: widget.layoutOptions,
        switching: widget.switching, error: widget.switchError})
    }
  }

  Process {
    id: switchProc
    onExited: function(exitCode) {
      if (exitCode !== 0) {
        root.switchQueue = []
        root.switchError = "Could not switch one of the keyboards. Please try again."
        root.broadcast("refresh")
        return
      }
      Qt.callLater(root.switchNext)
    }
  }

  property string layoutFull: ""
  // The keyboard the last reading spoke for, which is the one a click switches,
  // and separately the one activelayout named as being typed on. A reading
  // confirms the first is really there, so the click has a keyboard to reach
  // from the first reading onwards rather than only after a switch, and stops
  // naming one that has been unplugged.
  property string keyboardName: ""
  property string typedKeyboardName: ""
  property int activeLayoutIndex: 0
  // Keyboards on the seat, buttons and virtual ones excluded, and whether the
  // last reading left that shape in doubt.
  property int keyboardCount: 0
  property bool keyboardUnresolved: false
  // Nothing to read or switch on the single-layout install most people run, so
  // the widget ships on the bar and stays out of the way until there are two.
  // An older Hyprland that doesn't report the list keeps showing the label.
  property bool multipleLayouts: true
  // Short language code per layout description ("English (US)": "en"), read from
  // xkb's own table rather than maintained by hand.
  property var layoutBriefs: ({})
  readonly property string layoutLabel: KeyboardLayoutModel.shortLabel(layoutFull, layoutBriefs)

  // A query already in flight was started before this event, so it may read the
  // layout the switch replaced. Remember the request and re-run once it lands
  // rather than dropping it; nothing else would correct the label afterwards.
  property bool refreshPending: false

  function refresh() {
    if (queryProc.running) {
      refreshPending = true
      return
    }

    refreshPending = false
    queryProc.running = true
  }

  // Keyboards someone can actually type on, which is not everything Hyprland
  // calls a keyboard.
  function typedKeyboards(keyboards) {
    return keyboards.filter(k => KeyboardLayoutModel.isTypedKeyboard(k.name))
  }

  // The main flag names no keyboard for long: fcitx5 takes it with the virtual
  // keyboard it binds to inject, which leaves no typed keyboard holding it and
  // nothing to read at all, and once that unbinds it lands on whichever device
  // Hyprland saw last, a power button included. Go by layout progress instead,
  // and by the keyboard activelayout named.
  function selectKeyboard(typed) {
    return KeyboardLayoutModel.selectKeyboard(typed, root.typedKeyboardName)
  }

  // Cycle the configured choices, applying each by identity even when another
  // keyboard lists the same layouts in a different order.
  function cycleLayout() {
    if (!layoutOptions.length) return
    const position = layoutOptions.findIndex(option => option.index === activeLayoutIndex)
    selectLayout((position + 1) % layoutOptions.length)
  }

  Component.onCompleted: {
    briefsProc.running = true
    refresh()
  }

  Connections {
    target: Hyprland
    function onRawEvent(event) {
      if (!event || !event.name) return
      var name = String(event.name)
      // The event names the keyboard that switched ahead of the layout it moved
      // to, and that is the keyboard being typed on whatever holds the main flag.
      if (name === "activelayout") {
        const named = KeyboardLayoutModel.eventKeyboardName(event)
        if (named) root.typedKeyboardName = named
      }

      // A reload that adds a layout to kb_layout decides whether the widget
      // shows at all, and leaves every keyboard on the layout it was already
      // reading, so it raises no activelayout to notice it by.
      if (name.indexOf("activelayout") !== -1 || name === "configreloaded") root.refresh()
    }
  }

  Process {
    id: queryProc
    command: ["hyprctl", "-j", "devices"]
    onRunningChanged: {
      if (running) {
        stallTimer.restart()
        return
      }

      stallTimer.stop()
      if (root.refreshPending) root.refresh()
    }
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        let listed
        try {
          listed = JSON.parse(text || "{}").keyboards
        } catch (e) {
          return
        }

        // A query the watchdog killed reports nothing at all, and an empty
        // string parses into the same shape a seat with no keyboards would.
        // Tell them apart by the list itself, so only a reading that reached
        // hyprctl gets to speak for the seat.
        if (!Array.isArray(listed)) return

        const typed = root.typedKeyboards(listed)
        root.typedDevices = typed
        const kb = root.selectKeyboard(typed)
        root.currentKeyboard = kb || null
        if (!kb || !kb.active_keymap) {
          // Either the last keyboard has been unplugged, which the label has to
          // stop describing and the click has to stop naming, or keyboards are
          // there and none of them reports a keymap. Both leave the shape in
          // doubt, so keep asking rather than letting a count from before it
          // changed settle the poll.
          root.keyboardUnresolved = true
          if (typed.length === 0) {
            root.layoutFull = ""
            root.keyboardName = ""
          }
          return
        }

        root.keyboardUnresolved = false
        root.keyboardCount = typed.length
        root.keyboardName = String(kb.name || "")
        root.multipleLayouts = kb.layout === undefined || String(kb.layout).indexOf(",") !== -1
        root.activeLayoutIndex = kb.active_layout_index || 0
        root.layoutFull = kb.active_keymap
      }
    }
  }

  // The table only changes when xkb data is upgraded, so read it at startup and
  // leave it alone. The bar is built per monitor, so this runs once per widget.
  // The exotic rulesets cover layouts like trans (IPA) that ship in the same xkb
  // package and set just as well, so load them or those labels lose their code.
  Process {
    id: briefsProc
    command: ["xkbcli", "list", "--load-exotic"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        root.layoutBriefs = KeyboardLayoutModel.layoutBriefs(text)
        root.layoutCatalog = KeyboardLayoutModel.layoutCatalog(text)
      }
    }
  }

  Timer {
    id: refreshTimer
    interval: 600
    onTriggered: root.refresh()
  }

  // A query that never returns would freeze the label until the shell restarts,
  // since a Process that is already running can't be re-run. Give up on one that
  // overstays so the next refresh gets through, and ask again: the reading it
  // never delivered may have been the only one due on a settled seat, and
  // nothing else would come back for it.
  Timer {
    id: stallTimer
    interval: 5000
    onTriggered: {
      queryProc.running = false
      refreshTimer.restart()
    }
  }

  // Which keyboard on a crowded seat the label is describing can change without
  // Hyprland announcing it, since a device arriving or leaving raises no event
  // of its own, and that can only be learned by asking. Poll while there is that
  // ambiguity, until a first reading lands so a query that failed at login still
  // recovers, and while a reading has left the seat's shape in doubt. The
  // one-keyboard install has none of those, and is left alone rather than
  // spawning hyprctl forever for an answer that cannot change.
  Timer {
    interval: 10000
    running: !root.keyboardName || root.keyboardUnresolved || root.keyboardCount > 1
    repeat: true
    onTriggered: root.refresh()
  }

  visible: layoutLabel !== "" && multipleLayouts
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.layoutLabel
    fontSize: Style.font.caption
    horizontalMargin: 6
    tooltipText: root.layoutFull + "\nLeft-click: cycle · Super + middle-click: choose layout"
    onPressed: function(mouseButton) {
      if (mouseButton === Qt.LeftButton) root.cycleLayout()
      else if (mouseButton === Qt.MiddleButton || mouseButton === Qt.RightButton) root.choose()
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: menu
    contentWidth: panel.fittedContentWidth(Style.space(340))
    contentHeight: panel.fittedContentHeight(menu.implicitHeight)
    LayoutMenu {
      id: menu
      anchors.fill: parent
      options: root.layoutOptions
      activeIndex: root.activeLayoutIndex
      busy: switchProc.running
      error: root.switchError
      onSelected: function(index) { root.selectLayout(index) }
      onCloseRequested: root.close()
    }
  }
}
