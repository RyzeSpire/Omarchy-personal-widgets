// Label math for the keyboard layout widget, kept Qt-free so it can be unit
// tested under node (test/shell.d/keyboard-layout-test.sh).

// xkbcli list prints YAML, and every layout and variant block pairs a brief with
// the description hyprctl reports as the active keymap:
//
//   - layout: 'us'
//     variant: ''
//     brief: 'en'
//     description: English (US)
//
// The models and option groups it also prints carry no brief of their own, and
// a brief never carries past the block it was printed in, so neither reaches
// the table.
function layoutBriefs(text) {
  var briefs = {}
  var brief = ""

  String(text || "").split("\n").forEach(function (line) {
    if (/^\s*- /.test(line)) brief = ""

    var field = line.match(/^  (brief|description): (.*)$/)
    if (!field) return

    if (field[1] === "brief") {
      brief = field[2].replace(/^'|'$/g, "")
    } else if (brief) {
      briefs[field[2]] = brief
      brief = ""
    }
  })

  return briefs
}

// The brief is a short language code rather than a country one, which keeps the
// label sensible for the layouts named after a language: Esperanto reads EO and
// Arabic reads AR. It is the same code GNOME shows in its own indicator.
//
// Layouts missing from the table fall back to the first word of the description,
// which reads as ENG/POR but at least says something.
//
// Nearly every brief is a bare two-letter code, but a few tack a script onto it
// (Burmese (Zawgyi) is my-zwg) and the custom layout's is a word, so drop the
// script and cap the result at the same three characters the fallback gets.
// The widget sits between fixed neighbours on the bar and has no room to grow.
function shortLabel(description, briefs) {
  if (!description) return ""

  // A description like "constructor" reaches an inherited member rather than a
  // brief, so take the lookup only when it hands back the string it promises.
  var brief = (briefs || {})[description]
  var label = typeof brief === "string" && brief ? brief.split("-")[0] : description.split(/\s+/)[0]
  return label.substring(0, 3).toUpperCase()
}

// Hyprland's activelayout event pairs the keyboard that switched with the layout
// it moved to. Quickshell cuts the event into that many fields, so a description
// carrying a comma of its own stays in one piece; a binding old enough to hand
// back only the raw string gets split by hand. The virtual keyboard fcitx5 binds
// to inject announces switches too, and names a keyboard nobody types on.
function eventKeyboardName(event) {
  var parts

  try {
    if (event && event.parse) parts = event.parse(2)
  } catch (error) {
  }

  if (!parts) parts = String(event && event.data ? event.data : "").split(",")

  var name = String(parts[0] || "")
  return name.indexOf("hl-virtual-keyboard") === 0 ? "" : name
}

// Hyprland reports more than keyboards as keyboards. fcitx5 binds a virtual one
// to inject through, which keeps the us layout the input method gave it, and the
// ACPI power button, lid switch and sleep key each arrive carrying the seat's
// layout list without anyone ever typing on them. Both answer to switchxkblayout
// and both can hold the main flag, so a widget that reads or switches whatever
// the seat hands it ends up describing a button. Leave them out and what remains
// is keyboards, which is what the rest of this file can then assume.
//
// Missing a name here costs the accuracy the seat had before, never a keyboard:
// anything unrecognised stays in the list.
var UNTYPED_KEYBOARDS = /^(hl-virtual-keyboard|power-button|sleep-button|lid-switch|video-bus)/

function isTypedKeyboard(name) {
  return !UNTYPED_KEYBOARDS.test(String(name || ""))
}

// Every keyboard on the seat carries the same layout list unless one was given
// its own, but only the one being typed on advances through it. So the
// furthest-advanced is the one worth reading, and a switch names the keyboard it
// moved, which settles a seat holding two real keyboards outright.
//
// The name is taken whenever a keyboard still answers to it, wherever that
// keyboard sits in the list. Comparing positions instead would read the wrong
// keyboard the moment one wrapped from the last layout back to the first, which
// is the ordinary way round a pair of them. Applying a layout to the whole seat
// names a keyboard too, but leaves every one of them on the same layout, so the
// label reads the same whichever of them the name settles on.
function selectKeyboard(typed, namedByEvent) {
  var keyboards = typed || []

  return keyboards.find(function (keyboard) {
    return keyboard.name === namedByEvent
  }) || keyboards.reduce(function (furthest, keyboard) {
    return layoutIndex(keyboard) > layoutIndex(furthest) ? keyboard : furthest
  }, keyboards[0])
}

function layoutIndex(keyboard) {
  return (keyboard && keyboard.active_layout_index) || 0
}

// XKB's catalog supplies labels; only layouts already configured in Hyprland
// become menu choices. Unknown/custom variants keep their configured identity.
function unquote(value) {
  value = String(value || "").trim()
  if (value[0] === "'" && value[value.length - 1] === "'") return value.slice(1, -1).replace(/''/g, "'")
  return value
}

function layoutKey(code, variant) { return JSON.stringify([code, variant || ""]) }

function layoutCatalog(text) {
  var catalog = {}
  var record = null
  String(text || "").split("\n").forEach(function(line) {
    if (/^- /.test(line)) {
      var layout = line.match(/^- layout: (.*)$/)
      record = layout ? {code: unquote(layout[1]), variant: ""} : null
    }
    if (!record) return
    var field = line.match(/^  (variant|description): (.*)$/)
    if (!field) return
    if (field[1] === "variant") record.variant = unquote(field[2])
    else catalog[layoutKey(record.code, record.variant)] = unquote(field[2])
  })
  return catalog
}

function configuredLayouts(keyboard, catalog) {
  if (!keyboard || !keyboard.layout) return []
  var variants = String(keyboard.variant || "").split(",")
  return String(keyboard.layout).split(",").map(function(value, index) {
    var code = value.trim()
    var variant = String(variants[index] || "").trim()
    var key = layoutKey(code, variant)
    var label = (catalog || {})[key]
    if (typeof label !== "string" || !label) {
      label = (catalog || {})[layoutKey(code, "")] || code
      if (variant) label += " [" + variant + "]"
    }
    return {index: index, code: code, variant: variant, label: label}
  }).filter(function(option) { return option.code !== "" })
}

function selectionTargets(keyboards, option) {
  if (!option || typeof option.code !== "string" || !option.code) return []
  return (keyboards || []).filter(function(keyboard) {
    return keyboard.name && isTypedKeyboard(keyboard.name)
  }).map(function(keyboard) {
    var choice = configuredLayouts(keyboard, {}).find(function(item) {
      return item.code === option.code && item.variant === option.variant
    })
    return choice ? {name: String(keyboard.name), index: choice.index} : null
  }).filter(function(target) { return target !== null })
}

if (typeof module !== "undefined") {
  module.exports = {
    layoutCatalog: layoutCatalog,
    configuredLayouts: configuredLayouts,
    selectionTargets: selectionTargets,
    eventKeyboardName: eventKeyboardName,
    isTypedKeyboard: isTypedKeyboard,
    layoutBriefs: layoutBriefs,
    selectKeyboard: selectKeyboard,
    shortLabel: shortLabel
  }
}
