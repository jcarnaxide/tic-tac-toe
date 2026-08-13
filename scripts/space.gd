class_name Space extends Node2D

@export_range(0, 2) var coord_i: int = 0
@export_range(0, 2) var coord_j: int = 0

@onready var x_sprite = %XSprite
@onready var o_sprite = %OSprite

func reset():
	x_sprite.hide()
	o_sprite.hide()

func _handle_click():
	if GameState.is_valid_move(coord_i, coord_j):
		var player = GameState.whose_turn()
		if player == GameState.PLAYER.X:
			x_sprite.show()
		else:
			o_sprite.show()
		GameState.make_move(coord_i, coord_j)

func _on_click_area_input_event(_viewport, event, _shape_idx):
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				_handle_click()
