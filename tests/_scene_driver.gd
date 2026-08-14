class_name SceneDriver extends SceneTree

## Base class for `godot_verify.py drive` scenarios.
##
## Installed into the project by the drive command - do not edit here, edits are
## overwritten on refresh. The canonical copy lives in the godot-verify skill.
##
## Subclass it, override scenario(), and return an array of [seconds, Callable]
## steps. The harness owns everything that is easy to get wrong:
##
##   - a fixed timestep, so a tween can actually be observed part-way through
##   - one step per frame, so a sample is never taken before any delta ran
##   - a frame budget, so a scenario can never hang the caller
##   - a verdict, so a scenario that asserts nothing fails instead of passing
##
## Steps run in the order given; the times are absolute seconds from scene load,
## not deltas.

const DRIVER_VERSION := 1

var scene_root: Node

var _steps: Array = []
var _index := 0
var _elapsed := 0.0
var _passed := 0
var _failed := 0
var _aborted := false

# ---------------------------------------------------------------------------
# Override these
# ---------------------------------------------------------------------------

## Return an Array of [seconds: float, step: Callable].
func scenario() -> Array:
	return []

## Scene to boot. Defaults to the project's main scene.
func scene_path() -> String:
	return ""

# ---------------------------------------------------------------------------
# Helpers for use inside scenario()
# ---------------------------------------------------------------------------

## Fetch an autoload singleton. The global identifier (e.g. `GameState`) is NOT
## in scope under --script even though the node exists, so always come through
## here rather than naming the singleton directly.
func autoload(singleton: String) -> Node:
	var node := root.get_node_or_null(NodePath(singleton))
	if node == null:
		_abort("no autoload named %s - check the [autoload] section of project.godot"
			% singleton)
	return node

## Node lookup relative to the booted scene root. Accepts %UniqueNames.
func node(path: String) -> Node:
	if scene_root == null:
		_abort("scene root is not available yet")
		return null
	var found := scene_root.get_node_or_null(NodePath(path))
	if found == null:
		_abort("no node at %s under %s" % [path, scene_root.name])
	return found

## Every node of a given class in the booted scene.
func nodes_of_type(type_name: String) -> Array:
	if scene_root == null:
		return []
	return scene_root.find_children("*", type_name, true, false)

## Record an assertion. This is what makes a scenario mean something - a run
## that records none is reported as a failure, not a pass.
func expect(label: String, condition: bool) -> bool:
	if condition:
		_passed += 1
		print("DRIVE PASS  ", label)
	else:
		_failed += 1
		print("DRIVE FAIL  ", label)
	return condition

## Float-tolerant variant. Prints the actual value on failure, because "expected
## about 1.0" without the number just makes the reader run it again.
func expect_near(label: String, actual: float, target: float, epsilon := 0.001) -> bool:
	var ok := absf(actual - target) <= epsilon
	if ok:
		_passed += 1
		print("DRIVE PASS  ", label)
	else:
		_failed += 1
		print("DRIVE FAIL  ", label, "  (got ", actual, ", wanted ", target,
			" +/- ", epsilon, ")")
	return ok

## Assert a value sits strictly inside a range - the honest way to check that
## something is mid-flight rather than parked at either end.
func expect_between(label: String, actual: float, low: float, high: float) -> bool:
	var ok := actual > low and actual < high
	if ok:
		_passed += 1
		print("DRIVE PASS  ", label)
	else:
		_failed += 1
		print("DRIVE FAIL  ", label, "  (got ", actual, ", wanted strictly between ",
			low, " and ", high, ")")
	return ok

## Print a value without judging it. Useful while writing a scenario; an
## expectation should replace it before the scenario is kept.
func probe(label: String, value) -> void:
	print("DRIVE PROBE ", label, " = ", value)

# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

func _initialize() -> void:
	var path := scene_path()
	if path == "":
		path = str(ProjectSettings.get_setting("application/run/main_scene", ""))
	if path == "":
		_abort("no scene_path() override and the project sets no main scene")
		return

	var packed = load(path)
	if packed == null:
		_abort("could not load scene %s" % path)
		return

	scene_root = packed.instantiate()
	root.add_child(scene_root)
	print("DRIVE SCENE ", path)

	_steps = scenario()
	if _steps.is_empty() and not _aborted:
		_abort("scenario() returned no steps")

func _process(delta: float) -> bool:
	if _aborted:
		return true
	_elapsed += delta

	# One step per frame, deliberately. Firing two in a frame samples state
	# before the engine has processed a single delta between them, which makes
	# any "mid-animation" reading identical to the value at the start.
	if _index < _steps.size() and _elapsed >= float(_steps[_index][0]):
		var step = _steps[_index][1]
		_index += 1
		step.call()

	if _index >= _steps.size():
		_finish()
		return true
	return false

func _finish() -> void:
	print("DRIVE SUMMARY passed=", _passed, " failed=", _failed)
	print("DRIVE DONE")

func _abort(message: String) -> void:
	_aborted = true
	print("DRIVE ABORT ", message)
	print("DRIVE SUMMARY passed=", _passed, " failed=", _failed)
