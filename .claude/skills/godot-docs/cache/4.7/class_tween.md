# Tween (Godot 4.7)

Inherits: RefCounted < Object
Source: https://docs.godotengine.org/en/4.7/classes/class_tween.html

Lightweight object for animating a property over time. Not a Node — it is a
RefCounted created by the scene tree, never by `Tween.new()` (a manually
constructed Tween is invalid and cannot tween anything).

## Creating

- `Node.create_tween() -> Tween` — creates the tween AND binds it to that node.
- `SceneTree.create_tween() -> Tween` — unbound.

`bind_node(node: Node) -> Tween` halts the animation while the node is outside
the tree, and **kills the tween automatically when the bound node is freed**.
`Node.create_tween()` binds for you, so a tween made inside a node's own script
cannot outlive that node.

**Tweens start immediately on creation.** There is no `start()`. Only create one
at the moment you want motion to begin — creating one "ready to go" in `_ready()`
runs it at frame zero.

## Methods

```gdscript
tween_property(object: Object, property: NodePath, final_val: Variant, duration: float) -> PropertyTweener
tween_callback(callback: Callable) -> CallbackTweener
set_trans(trans: TransitionType) -> Tween
set_ease(ease: EaseType) -> Tween
set_parallel(parallel: bool = true) -> Tween
parallel() -> Tween
chain() -> Tween
kill() -> void
is_valid() -> bool
is_running() -> bool
stop() -> void
pause() -> void
play() -> void
```

Signal: `finished()` — emitted when all tweening is done.

## TransitionType
`TRANS_LINEAR`, `TRANS_SINE`, `TRANS_QUINT`, `TRANS_QUART`, `TRANS_QUAD`,
`TRANS_EXPO`, `TRANS_ELASTIC`, `TRANS_CUBIC`, `TRANS_CIRC`, `TRANS_BOUNCE`,
`TRANS_BACK`, `TRANS_SPRING`

## EaseType
`EASE_IN`, `EASE_OUT`, `EASE_IN_OUT`, `EASE_OUT_IN`

`TRANS_BACK` + `EASE_OUT` overshoots the target then settles — the standard
"pop in" curve.

## Notes

Steps are **sequential by default**: consecutive `tween_property()` calls run one
after another. For simultaneous motion use `set_parallel(true)` (applies to every
subsequent step) or `parallel()` (applies to the next step only). `chain()` ends
a parallel run and returns to sequential.

The docs warn: **avoid more than one Tween per object's property.** Two live
tweens writing the same property fight each other and the result depends on
execution order. The safe idiom when a tween can be retriggered:

```gdscript
var _tween: Tween

func _pop() -> void:
    if _tween and _tween.is_valid():
        _tween.kill()
    _tween = create_tween()
    _tween.tween_property(self, "scale", Vector2.ONE, 0.15) \
        .set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
```

A finished tween becomes invalid but the reference stays alive, so guard with
`is_valid()` rather than a bare null check — the docs do not define `kill()` on
an already-finished tween.

`tween_property` takes a **NodePath**, so a plain string names a property
(`"scale"`) and a subpath names a component (`"modulate:a"`). A misspelled
property name is NOT caught by `--check-only`; it fails silently or errors at
runtime.
