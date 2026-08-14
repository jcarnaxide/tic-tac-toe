extends Node

signal player_changed(player: PLAYER)
signal game_over(winner)
## Emitted for every accepted move so the board can render itself.
signal board_changed(i: int, j: int, player: PLAYER)
signal board_reset

enum PLAYER { X, O }

const SIZE = 3

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
var _finished := false

func reset():
	_board = []
	for i in SIZE:
		var row := []
		row.resize(SIZE)  # resize fills with null
		_board.append(row)
	_finished = false
	_current_player = PLAYER.X
	board_reset.emit()

func whose_turn() -> PLAYER:
	return _current_player

func is_valid_move(i: int, j: int) -> bool:
	return not _finished and _board[i][j] == null

func make_move(i: int, j: int):
	# Validate here rather than trusting the caller - the end screen happens to
	# block clicks once the game is over, but that is a UI accident, not a rule.
	if not is_valid_move(i, j):
		return
	var player := _current_player
	_board[i][j] = player
	board_changed.emit(i, j, player)
	# `!= null` rather than truthiness: PLAYER.X is 0, so a truthiness test drops
	# every win by X. _check_winner() returns null or a PLAYER, never a bool.
	var winner = _check_winner()
	if winner != null or _is_board_full():
		_finished = true
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

func _is_board_full() -> bool:
	for row in _board:
		for cell in row:
			if cell == null:
				return false
	return true
