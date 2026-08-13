# Godot Anti-Patterns

Common Godot 4.x mistakes with their fixes. Consult when something smells
familiar and you want the canonical correction.

Behaviours marked **[verified]** were tested against Godot 4.7.1 rather than
taken from folklore - several widely repeated "rules" turn out to be false, and
recommending them produces review findings that are worse than silence.

**Contents:** [Performance](#performance) · [Memory and lifetime](#memory-and-lifetime) ·
[Signals](#signals) · [Logic](#logic) · [Architecture](#architecture) ·
[4.x migration](#godot-4x-migration)

---

## Performance

Apply these to code that runs every frame. In `_ready()` or a click handler they
are noise, and flagging them there trains the reader to ignore you.

### Node lookup in a per-frame loop

```gdscript
# BAD - resolves the path from scratch every frame
func _process(delta: float) -> void:
	$Player/Sprite2D.modulate.a -= delta

# GOOD
@onready var sprite: Sprite2D = $Player/Sprite2D

func _process(delta: float) -> void:
	sprite.modulate.a -= delta
```

### Allocating in hot paths

```gdscript
# BAD - a new node every frame
func _process(delta: float) -> void:
	var particles := PARTICLES.instantiate()
	add_child(particles)

# GOOD - pool and reuse
const PARTICLES := preload("res://particles.tscn")
var _pool: Array[GPUParticles2D] = []

func emit_particles() -> void:
	_get_pooled().restart()
```

`preload()` is resolved at parse time, so it costs nothing at runtime even
written inline - the expense is `instantiate()` and `add_child()`. Flagging
`preload` itself is a false positive.

### Building strings by concatenation in a loop

```gdscript
# BAD - reallocates on every iteration
var result := ""
for i in range(1000):
	result += str(i) + ","

# GOOD
var parts: PackedStringArray = []
for i in range(1000):
	parts.append(str(i))
var result := ",".join(parts)
```

### Scanning children every frame to find a type

```gdscript
# BAD
func _process(delta: float) -> void:
	for child in get_children():
		if child is Enemy:
			child.update(delta)

# GOOD - groups are the engine's answer to "all the things of kind X"
# in Enemy._ready(): add_to_group("enemies")
func _process(delta: float) -> void:
	for enemy in get_tree().get_nodes_in_group("enemies"):
		enemy.update(delta)
```

Groups are maintained by the engine, so membership stays correct as nodes are
added and freed without any bookkeeping of your own.

---

## Memory and lifetime

### Hiding instead of freeing

```gdscript
# BAD - still in the tree, still processing
func die() -> void:
	visible = false

# GOOD
func die() -> void:
	queue_free()
```

Use `queue_free()`, not `free()` - it defers deletion to a safe point rather
than deleting mid-frame while something may still be iterating the node.

If the object is genuinely being recycled, disable it properly rather than just
hiding it:

```gdscript
func recycle() -> void:
	visible = false
	set_process(false)
	set_physics_process(false)
```

### Circular references

This is a **coupling** problem for Nodes and a **memory** problem for
`RefCounted`. Godot frees Nodes manually, so a Node cycle doesn't leak - it just
makes both halves untestable and unreusable. `RefCounted` and `Resource` use
reference counting, so a genuine cycle there never reaches zero and does leak.

```gdscript
# BAD - each half needs the other to exist
# weapon.gd  ->  var owner_player: Player
# player.gd  ->  var current_weapon: Weapon

# GOOD - the child announces, the parent listens
# weapon.gd
signal fired(damage: int)

# player.gd connects to it and keeps the one-way reference downward
```

---

## Signals

### Signals do NOT leak when a node is freed **[verified]**

Godot disconnects every connection belonging to an object when that object is
freed - including connections to long-lived autoloads. Tested on 4.7.1: an
autoload signal showed `connections=1` while a listener node was alive and
`connections=0` after `queue_free()`, and emitting afterwards ran clean.

```gdscript
# This is FINE. No cleanup required.
func _ready() -> void:
	GlobalEvents.game_over.connect(_on_game_over)
```

Manual `_exit_tree()` disconnect boilerplate for this case is unnecessary. Do
not flag it in review.

### Connecting the same method twice errors loudly **[verified]**

```gdscript
ping.connect(_on_ping)
ping.connect(_on_ping)
# ERROR: Signal 'ping' is already connected to given callable ... in that object.
```

The connection count stays at 1 - Godot refuses the duplicate rather than
double-firing. Because it is loud and self-correcting, this is a bug you find
immediately, not one worth defensive `is_connected()` guards.

Note that `_ready()` runs **once per node instance**, so wiring signals there is
correct and needs no guard. A fresh scene instance has fresh, unconnected nodes.
Guarding it is cargo cult.

### The real footgun: reconnecting lambdas **[verified]**

```gdscript
# BAD - if this runs more than once, handlers multiply silently
func start_round() -> void:
	timer.timeout.connect(func(): _on_tick())
```

Every lambda literal is a *distinct* Callable, so Godot cannot recognise the
duplicate and has nothing to warn about. Tested on 4.7.1: two identical-looking
lambdas produced two separate connections and both fired. Connect twice and the
handler runs twice, three times and it runs three times - no error, just a
mysterious multiplier.

```gdscript
# GOOD - a named method is a stable Callable the engine can dedupe
func start_round() -> void:
	if not timer.timeout.is_connected(_on_tick):
		timer.timeout.connect(_on_tick)

# ALSO GOOD - fires once, then cleans itself up
timer.timeout.connect(_on_tick, CONNECT_ONE_SHOT)
```

Lambdas are fine for connections made once, in `_ready()`. The danger is only in
code that can run repeatedly.

### Awaiting a signal that may never fire

```gdscript
# RISKY - if the node is freed while suspended, execution never resumes
await animation_finished
queue_free()

# SAFER - confirm the node still exists before touching it
await animation_finished
if is_instance_valid(self):
	queue_free()
```

---

## Logic

### State as a pile of booleans

```gdscript
# BAD - 4 bools allow 16 states when only 4 are legal
var is_walking := false
var is_running := false
var is_jumping := false

# GOOD - invalid combinations become unrepresentable
enum State { IDLE, WALKING, RUNNING, JUMPING }
var state: State = State.IDLE
```

### Deep nesting

```gdscript
# BAD
func process_input() -> void:
	if is_alive:
		if has_weapon:
			if weapon.has_ammo:
				fire()

# GOOD - guard clauses keep the happy path flat
func process_input() -> void:
	if not is_alive:
		return
	if not has_weapon:
		return
	if not weapon.has_ammo:
		return
	fire()
```

### Magic numbers

```gdscript
# BAD
if position.y > 1080:
	queue_free()

# GOOD
const DESPAWN_Y := 1080.0

if position.y > DESPAWN_Y:
	queue_free()
```

Worth flagging when the number appears more than once, or when its meaning isn't
obvious from context. A lone `0.5` in a lerp is fine.

---

## Architecture

### God autoload

```gdscript
# BAD - one singleton owning everything
# GameManager.gd: score, health, level, settings, inventory,
#                 save_game(), play_sound(), spawn_enemy()

# GOOD - separate concerns, each independently testable
# ScoreManager.gd, PlayerData.gd, AudioManager.gd, SaveSystem.gd
```

The most common structural failure in solo Godot projects, and the hardest to
unwind once everything depends on it. Autoloads are global state - justified for
things that are genuinely global (audio bus, save system, event bus), not as a
convenient place to put whatever needs sharing.

### Reaching across the tree

```gdscript
# BAD - welds this node to a scene layout it does not own
func take_damage(amount: int) -> void:
	health -= amount
	get_node("/root/Game/UI/HealthBar").value = health

# GOOD - announce, don't reach
signal health_changed(new_health: int)

func take_damage(amount: int) -> void:
	health -= amount
	health_changed.emit(health)
```

The rule of thumb: **signals go up, direct calls go down.** A parent may call
into its children; a child should signal and let whoever cares listen. Absolute
paths like `/root/Game/UI/...` are the clearest symptom - they break when the
scene is reorganised and make the node impossible to instantiate alone.

### Duplicated knowledge

The same rule encoded in two places drifts apart silently. Win conditions in both
the board and the UI, grid size as a literal in four files, a colour repeated in
five scenes. Put it in one place - a constant, an autoload, a resource - and read
it from there.

---

## Godot 4.x migration

Old 3.x patterns that no longer work:

```gdscript
# OLD (3.x)                          # NEW (4.x)
connect("pressed", self, "_on_x")    pressed.connect(_on_x)
emit_signal("died")                  died.emit()
yield(get_tree(), "idle_frame")      await get_tree().process_frame
export var speed = 10                @export var speed: float = 10.0
export(int, 0, 100) var hp = 100     @export_range(0, 100) var hp: int = 100
instance()                           instantiate()
get_tree().change_scene(path)        get_tree().change_scene_to_file(path)
rand_range(a, b)                     randf_range(a, b)
OS.get_ticks_msec()                  Time.get_ticks_msec()
```

Prefer where available: `@onready` over assignment in `_ready()`, typed arrays
(`Array[Enemy]`) over bare `Array`, and `StringName` (`&"name"`) for dictionary
keys and group names in hot paths.
