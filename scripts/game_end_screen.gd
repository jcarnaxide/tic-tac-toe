class_name GameEndScreen extends Control

signal play_again_requested

@onready var winner = %Winner
@onready var x_texture = %XTexture
@onready var o_texture = %OTexture
@onready var tie = %Tie
@onready var play_again_button = %PlayAgainButton

func _ready():
	play_again_button.pressed.connect(_on_play_again_button_pressed)

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


func _on_play_again_button_pressed():
	play_again_requested.emit()
