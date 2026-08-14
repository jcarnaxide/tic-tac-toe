class_name Space extends Node2D

@export_range(0, 2) var coord_i: int = 0
@export_range(0, 2) var coord_j: int = 0

const POP_DURATION := 0.15

@onready var x_sprite: Sprite2D = %XSprite
@onready var o_sprite: Sprite2D = %OSprite

var _tween: Tween

func _ready():
	$ClickArea.input_event.connect(_on_click_area_input_event)
	GameState.board_changed.connect(_on_board_changed)
	GameState.board_reset.connect(_on_board_reset)

func _on_board_changed(i: int, j: int, player):
	if i != coord_i or j != coord_j:
		return
	var placed := x_sprite if player == GameState.PLAYER.X else o_sprite
	var other := o_sprite if player == GameState.PLAYER.X else x_sprite
	other.hide()
	_pop_in(placed)

func _on_board_reset():
	# Kill first: a pop still running would keep writing scale after the reset,
	# and the next round's _pop_in() would be fighting it for the same property.
	_kill_tween()
	x_sprite.hide()
	o_sprite.hide()

## Scales the sprite up from nothing with a slight overshoot. Sprite2D is
## centered by default, so this pops from the middle of the space.
func _pop_in(sprite: Sprite2D):
	_kill_tween()
	sprite.scale = Vector2.ZERO
	sprite.show()
	# create_tween() binds to this node, so the tween dies with the Space.
	_tween = create_tween()
	_tween.tween_property(sprite, "scale", Vector2.ONE, POP_DURATION) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

func _kill_tween():
	# A finished tween goes invalid while the reference stays live, so the
	# is_valid() check is the guard that matters - not a null check.
	if _tween and _tween.is_valid():
		_tween.kill()

func _handle_click():
	# GameState validates and reports back via board_changed - this space does
	# not decide whether the move is legal or what it should draw.
	GameState.make_move(coord_i, coord_j)

func _on_click_area_input_event(_viewport, event, _shape_idx):
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				_handle_click()
