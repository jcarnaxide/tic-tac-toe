# GDScript Style Checklist

Conventions from the [official GDScript style
guide](https://docs.godotengine.org/en/4.7/tutorials/scripting/gdscript/gdscript_styleguide.html).

**Use this for citing a specific rule, not for walking top to bottom.** A review
that lists every missing type hint buries the finding that mattered. Style is the
lowest-priority review category - see SKILL.md for why.

## Naming

| Thing | Convention | Example |
|---|---|---|
| Class (`class_name`) | `PascalCase` | `PlayerController` |
| Node names in scenes | `PascalCase` | `HealthBar` |
| Functions, variables | `snake_case` | `move_speed`, `get_health()` |
| Constants | `CONSTANT_CASE` | `MAX_HEALTH` |
| Enum type | `PascalCase` | `enum State` |
| Enum members | `CONSTANT_CASE` | `State.GAME_OVER` |
| Private members | `_` prefix | `_internal_state` |
| Signals | past tense | `health_changed`, `died` |
| Booleans | `is_` / `has_` / `can_` | `is_alive`, `has_ammo` |
| Files | `snake_case.gd` | `player_controller.gd` |

Signals name what *happened*, not what to do about it - `health_changed`, not
`update_health_bar`. A signal named after its handler has the coupling backwards.

## Typing

Static types let the analyser catch mistakes before the game runs, which is the
main argument for them - `godot-verify check` reports type errors only where
types exist to check.

```gdscript
var speed: float = 10.0
var cells: Array[int] = []
func take_damage(amount: int) -> void:
func get_name() -> String:
```

- Annotate function parameters and return types, including `-> void`.
- Prefer typed arrays (`Array[Enemy]`) over bare `Array`.
- `:=` infers the type and is preferred where the right-hand side is unambiguous:
  `var speed := 10.0`.
- Avoid `Variant` unless the value genuinely varies.

## File structure

Declaration order, top to bottom:

```gdscript
@tool
class_name MyClass
extends Node

## Docstring describing the class.

signal something_happened(value: int)

enum State { IDLE, ACTIVE }

const MAX_ITEMS := 10

@export var speed: float = 100.0

var _private_state := 0

@onready var sprite: Sprite2D = $Sprite2D

func _ready() -> void:
	pass

func public_method() -> void:
	pass

func _private_method() -> void:
	pass
```

Godot's built-in callbacks (`_ready`, `_process`, `_input`) conventionally come
before your own methods.

## Formatting

- **Tabs** for indentation. Godot uses tabs; mixing spaces causes parse errors.
- Two blank lines between top-level functions, one between blocks inside them.
- Line length ~100 characters.
- Spaces around operators and after commas.
- No space before `:` in type hints: `var x: int`, not `var x : int`.

## Structure smells

Worth raising only when they actually impede reading:

- A function doing several unrelated things.
- Nesting past ~3 levels - usually solved with guard clauses.
- `extends` missing or implicit.
- `class_name` missing on a script used as a type elsewhere.
- Commented-out code left in place.
- A comment restating what the code says rather than why.

## Comments and docstrings

`##` docstrings surface in the editor's help panel and feed
`godot --gdscript-docs`:

```gdscript
## Applies damage and emits [signal health_changed].
## Returns true if this brought health to zero.
func take_damage(amount: int) -> bool:
```

Comments should explain *why*, not restate the code. `# add 1 to score` earns
nothing; `# offset by 1 because the grid is 1-indexed in save files` earns its
line.
