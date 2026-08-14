extends Node2D

@onready var game_end_screen: GameEndScreen = %GameEndScreen

func _ready():
	GameState.game_over.connect(_on_game_over)

func _on_game_over(winner):
	game_end_screen.set_winner(winner)
	game_end_screen.show()

func _reset():
	# Spaces clear themselves in response to board_reset.
	GameState.reset()
	game_end_screen.hide()
