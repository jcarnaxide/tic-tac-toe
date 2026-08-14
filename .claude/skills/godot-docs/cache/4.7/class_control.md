# Control (Godot 4.7) — transform and mouse filtering

Inherits: CanvasItem < Node < Object
Source: https://docs.godotengine.org/en/4.7/classes/class_control.html

Partial entry: covers the pivot/scale and mouse-filter members only. The upstream
page is large and both fetches of it truncated before the Signals and MouseFilter
enum sections, so the values below were confirmed by running the engine headless
rather than read from the page. See "Verified by probe".

## Transform

- `pivot_offset: Vector2 = Vector2(0, 0)` — the origin for `rotation` and
  `scale`. **Defaults to the top-left corner**, so scaling a Control grows it
  down-and-right out of its corner rather than from its middle. For a centred
  pop, set `pivot_offset = size / 2.0`.
- `scale: Vector2 = Vector2(1, 1)`
- `size: Vector2` — the bounding rectangle, driven by anchors/offsets and by the
  parent container. Not final until layout has run, so reading `size` in
  `_ready()` can give a stale value.

Because `size` settles after `_ready()`, keep the pivot correct by reacting to
the engine's own signal instead of guessing at timing:

```gdscript
func _ready() -> void:
    resized.connect(_recenter_pivot)
    _recenter_pivot()

func _recenter_pivot() -> void:
    pivot_offset = size / 2.0
```

## Signals

- `resized()` — **takes no arguments.** Emitted when the control's size changes.
- `minimum_size_changed()` — also no arguments.

## MouseFilter

`mouse_filter: MouseFilter = MOUSE_FILTER_STOP`

| Constant | Value | Effect |
|---|---|---|
| `MOUSE_FILTER_STOP` | 0 | Consumes mouse/touch events. **The default.** |
| `MOUSE_FILTER_PASS` | 1 | Handles the event, then lets it continue to nodes underneath. |
| `MOUSE_FILTER_IGNORE` | 2 | Ignores events entirely; they fall straight through. |

The default being `STOP` is the load-bearing detail: **any** full-rect Control
laid over the scene silently eats mouse input aimed at the 2D world below it,
including `Area2D.input_event` picking, with no code saying so. A fading-out
overlay keeps blocking for the whole fade unless it is switched to
`MOUSE_FILTER_IGNORE` when the fade starts.

## Verified by probe

Run headless against 4.7.1.stable, since the docs page truncated:

```gdscript
extends SceneTree
func _init():
    print(Control.MOUSE_FILTER_IGNORE)   # 2
    print(Control.MOUSE_FILTER_STOP)     # 0
    print(Control.MOUSE_FILTER_PASS)     # 1
    var c := Control.new()
    print(c.mouse_filter)                # 0
    for s in c.get_signal_list():
        if s.name == "resized": print(s.args)   # []
    c.free()
    quit()
```

`godot --headless --script res://probe.gd` runs a script directly, provided it
`extends SceneTree` and calls `quit()`. Useful for settling any API question the
docs leave ambiguous.
