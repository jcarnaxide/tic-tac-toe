extends Node2D

@onready var spaces_parent = %SpacesParent
@onready var game_end_screen: GameEndScreen = %GameEndScreen

func _ready():
	GameState.game_over.connect(func(winner):
		print("Winner: %s" % winner)
		game_end_screen.set_winner(winner)
		game_end_screen.show()
	)

func _reset():
	for space: Space in spaces_parent.get_children():
		space.reset()
	GameState.reset()
	game_end_screen.hide()
