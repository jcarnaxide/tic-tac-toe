class_name Space extends Node2D

@export_range(0, 2) var coord_i: int = 0
@export_range(0, 2) var coord_j: int = 0

@onready var x_sprite: Sprite2D = %XSprite
@onready var o_sprite: Sprite2D = %OSprite

func _ready():
	$ClickArea.input_event.connect(_on_click_area_input_event)
	GameState.board_changed.connect(_on_board_changed)
	GameState.board_reset.connect(_on_board_reset)

func _on_board_changed(i: int, j: int, player):
	if i != coord_i or j != coord_j:
		return
	x_sprite.visible = player == GameState.PLAYER.X
	o_sprite.visible = player == GameState.PLAYER.O

func _on_board_reset():
	x_sprite.hide()
	o_sprite.hide()

func _handle_click():
	# GameState validates and reports back via board_changed - this space does
	# not decide whether the move is legal or what it should draw.
	GameState.make_move(coord_i, coord_j)

func _on_click_area_input_event(_viewport, event, _shape_idx):
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				_handle_click()
