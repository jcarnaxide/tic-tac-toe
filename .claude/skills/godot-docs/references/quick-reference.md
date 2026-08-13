# GDScript Quick Reference (Godot 4.x)

Syntax and idioms that are stable across 4.x releases. Most everyday questions
are answered here without a fetch. For a specific class's members, resolve and
fetch the version-matched page instead - those do change between releases.

**Contents:** [Variables](#variables) · [Functions](#functions) ·
[Lifecycle](#node-lifecycle) · [Signals](#signals) · [Node access](#node-access) ·
[Exports](#export-annotations) · [Patterns](#common-patterns) ·
[2D nodes](#common-2d-nodes) · [UI nodes](#common-ui-nodes) · [3D](#3d)

## Variables

```gdscript
var count = 10                  # inferred, dynamically typed
var count := 10                 # inferred, statically typed (preferred)
var count: int = 10             # explicit
const MAX_SPEED := 200.0        # compile-time constant
static var instances := 0       # shared across all instances
var cells: Array[int] = []      # typed array
```

## Functions

```gdscript
func take_damage(amount: int) -> void:
	health -= amount

func get_display_name() -> String:
	return name.capitalize()

func find_target(radius: float = 100.0) -> Node2D:   # default argument
	return null

# Lambdas
var double := func(x: int) -> int: return x * 2
```

## Node lifecycle

In call order:

| Callback | When |
|---|---|
| `_init()` | Object constructed, before entering the tree |
| `_enter_tree()` | Node added to the scene tree; children not yet ready |
| `_ready()` | Node **and all its children** are ready. Runs once per instance |
| `_process(delta)` | Every rendered frame; `delta` varies |
| `_physics_process(delta)` | Fixed timestep (60Hz default). Physics and movement |
| `_input(event)` | Unhandled input events |
| `_exit_tree()` | Node removed from the tree |

`_enter_tree()` fires top-down, `_ready()` bottom-up - which is why `_ready()`
can safely touch children but `_enter_tree()` cannot. Because `_ready()` runs
exactly once per instance, wiring signals there needs no duplicate guard.

Put anything frame-rate sensitive in `_physics_process`; `_process` runs at the
display rate and will behave differently on a 144Hz monitor.

## Signals

```gdscript
signal health_changed(new_health: int)      # declare (typed params preferred)

health_changed.emit(health)                 # emit

node.health_changed.connect(_on_health_changed)          # connect
node.health_changed.connect(_on_tick, CONNECT_ONE_SHOT)  # auto-disconnects
node.pressed.connect(_on_pressed.bind(index))            # pass extra args

await node.health_changed                   # suspend until it fires
```

`bind()` appends its arguments to whatever the signal itself emits, which is how
you give many identical buttons one shared handler that knows which was pressed.

Connections are removed automatically when either object is freed - no manual
cleanup needed. But every lambda literal is a *distinct* Callable, so connecting
a lambda in code that runs more than once silently stacks duplicate handlers.
Use a named method there.

## Node access

```gdscript
$Sprite2D                       # direct child
$Panel/Label                    # nested path
$"../Sibling"                   # quotes needed for paths with . or /
%HealthBar                      # unique name (set "Access as Unique Name")
get_node("Path/To/Node")        # same as $, but accepts a runtime string
get_node_or_null("Maybe")       # null instead of an error when absent
get_parent()
get_children()
get_tree().get_nodes_in_group("enemies")
```

`$Path` and `get_node()` raise if the path is wrong. Use `get_node_or_null()`
plus a guard only where the node is genuinely optional - guarding a
structurally guaranteed node hides real breakage.

`%UniqueName` survives moving a node around the scene, unlike a `$Path`.

## Export annotations

```gdscript
@export var speed: float = 100.0
@export_range(0, 100) var health: int = 100
@export_enum("Walk", "Run", "Jump") var mode: int
@export_file("*.png") var texture_path: String
@export_multiline var description: String
@export_group("Movement")            # groups everything after it
@export var target: Node2D            # node picker in the inspector

@onready var sprite: Sprite2D = $Sprite2D   # assigned just before _ready()
```

`@onready` exists because `$Sprite2D` is null during `_init()` - the children
don't exist yet at variable-initialisation time.

## Common patterns

```gdscript
# Instantiate a scene
const ENEMY := preload("res://enemy.tscn")     # parse-time, no runtime cost
var enemy := ENEMY.instantiate()
add_child(enemy)

# load() for a path only known at runtime
var scene := load(path) as PackedScene

# Change scene
get_tree().change_scene_to_file("res://menu.tscn")
get_tree().change_scene_to_packed(ENEMY)

# Wait
await get_tree().create_timer(1.0).timeout
await get_tree().process_frame

# Tween
var tween := create_tween()
tween.tween_property(self, "position", Vector2(100, 100), 1.0)
tween.tween_callback(queue_free)

# Input
func _input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_accept"):
		confirm()

func _physics_process(delta: float) -> void:
	var direction := Input.get_axis("ui_left", "ui_right")
	velocity.x = direction * speed

# Groups
add_to_group("enemies")
for enemy in get_tree().get_nodes_in_group("enemies"):
	enemy.take_damage(10)
```

## Common 2D nodes

| Node | Purpose |
|---|---|
| `Node2D` | Base 2D node with a transform |
| `Sprite2D` | Display a texture |
| `AnimatedSprite2D` | Sprite with frame animations |
| `CharacterBody2D` | Player/enemy with direct movement control |
| `RigidBody2D` | Physics-driven body |
| `StaticBody2D` | Immovable collision |
| `Area2D` | Overlap detection, triggers, pickups |
| `CollisionShape2D` | Collision bounds (child of a body or area) |
| `Camera2D` | 2D camera |
| `TileMapLayer` | Tile-based levels |
| `CanvasLayer` | UI layer, unaffected by camera movement |

## Common UI nodes

| Node | Purpose |
|---|---|
| `Control` | Base UI node with anchors and margins |
| `Label` | Display text |
| `RichTextLabel` | BBCode-formatted text |
| `Button` | Clickable button; `pressed` signal |
| `TextureButton` | Button with textures instead of a theme |
| `LineEdit` | Single-line text input |
| `Panel` | Background panel |
| `VBoxContainer` / `HBoxContainer` | Stack children vertically / horizontally |
| `GridContainer` | Grid layout; set `columns` |
| `MarginContainer` | Add padding around children |
| `CenterContainer` | Centre a single child |
| `AspectRatioContainer` | Keep a child at a fixed aspect ratio |

Containers control their children's position and size - setting `position` on a
node inside a container has no effect. Use `custom_minimum_size` and the
`size_flags_*` properties instead.

## 3D

Common nodes: `Node3D`, `MeshInstance3D`, `CharacterBody3D`, `RigidBody3D`,
`StaticBody3D`, `Area3D`, `CollisionShape3D`, `Camera3D`,
`DirectionalLight3D` / `OmniLight3D` / `SpotLight3D`, `WorldEnvironment`,
`RayCast3D`, `NavigationRegion3D`, `AudioStreamPlayer3D`.

Most 2D concepts map directly - the physics bodies, areas, and collision shapes
behave the same way with an extra axis. For 3D specifics (transforms and bases,
navigation meshes, lighting and environment settings), fetch the version-matched
class pages rather than working from the 2D analogy.
