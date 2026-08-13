extends Node

signal player_changed(player: PLAYER)
signal game_over(winner)

enum PLAYER { X = 1, O = 2 }

const CONSECUTIVES = [
	## Horizontals
	[[0,0], [0,1], [0,2]],
	[[1,0], [1,1], [1,2]],
	[[2,0], [2,1], [2,2]],
	## Verticles
	[[0,0], [1,0], [2,0]],
	[[0,1], [1,1], [2,1]],
	[[0,2], [1,2], [2,2]],
	## Diagonals
	[[0,0], [1,1], [2,2]],
	[[0,2], [1,1], [2,0]],
]

var _current_player: PLAYER = PLAYER.X:
	set(v):
		_current_player = v
		player_changed.emit(_current_player)

var _board: Array

func reset():
	_board = [
		[null, null, null],
		[null, null, null],
		[null, null, null],
	]
	_current_player = PLAYER.X

func whose_turn() -> PLAYER:
	return _current_player

func is_valid_move(i: int, j: int) -> bool:
	return _board[i][j] == null

func make_move(i: int, j: int):
	_board[i][j] = _current_player
	var winner = _check_winner()
	if winner or _is_board_full():
		game_over.emit(winner)
	else:
		_next_player()

func _ready():
	reset()

func _next_player():
	if _current_player == PLAYER.X:
		_current_player = PLAYER.O
	else:
		_current_player = PLAYER.X

func _check_winner():
	for player in PLAYER.values():
		for consecutive in CONSECUTIVES:
			var is_win := true
			for coord in consecutive:
				var i = coord[0]
				var j = coord[1]
				if player != _board[i][j]:
					is_win = false
			if is_win:
				return player

func _is_board_full():
	for i in range(3):
		for j in range(3):
			if _board[i][j] == null:
				return false
	return true
