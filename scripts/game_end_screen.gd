class_name GameEndScreen extends Control

signal play_again_requested

const APPEAR_DURATION := 0.25
const DISMISS_DURATION := 0.15
const APPEAR_FROM_SCALE := 0.8

@onready var winner = %Winner
@onready var x_texture = %XTexture
@onready var o_texture = %OTexture
@onready var tie = %Tie
@onready var play_again_button = %PlayAgainButton
@onready var _panel: PanelContainer = $PanelContainer

var _tween: Tween

func _ready():
	play_again_button.pressed.connect(_on_play_again_button_pressed)
	# A Control scales around pivot_offset, which defaults to the top-left - the
	# panel would grow out of its own corner. Track the size via the engine's own
	# signal rather than guessing when layout has settled.
	_panel.resized.connect(_recenter_pivot)
	_recenter_pivot()

func _recenter_pivot():
	_panel.pivot_offset = _panel.size / 2.0

func reset():
	winner.hide()
	x_texture.hide()
	o_texture.hide()
	tie.hide()

func set_winner(game_winner):
	reset()
	if game_winner == null:
		tie.show()
		return
	winner.show()
	if game_winner == GameState.PLAYER.X:
		x_texture.show()
	elif game_winner == GameState.PLAYER.O:
		o_texture.show()

## Fades and pops the screen in. Call after set_winner() so the panel is sized
## for its final contents.
func appear():
	_kill_tween()
	mouse_filter = Control.MOUSE_FILTER_STOP
	modulate.a = 0.0
	_panel.scale = Vector2.ONE * APPEAR_FROM_SCALE
	show()
	_tween = create_tween().set_parallel()
	_tween.tween_property(self, "modulate:a", 1.0, APPEAR_DURATION) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_tween.tween_property(_panel, "scale", Vector2.ONE, APPEAR_DURATION) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

## Fades the screen out, then hides it.
func dismiss():
	if not visible:
		return
	_kill_tween()
	# Still a full-rect Control while it fades, and MOUSE_FILTER_STOP is the
	# default - without this it swallows clicks on the board underneath for the
	# whole dismiss. appear() puts it back.
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_tween = create_tween()
	_tween.tween_property(self, "modulate:a", 0.0, DISMISS_DURATION) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	_tween.tween_callback(hide)

func _kill_tween():
	if _tween and _tween.is_valid():
		_tween.kill()

func _on_play_again_button_pressed():
	play_again_requested.emit()
