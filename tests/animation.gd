extends SceneDriver

## Covers the two things `check` and `smoke` structurally cannot see: that the
## piece pop and the win-screen transition actually interpolate over time, and
## that resetting mid-animation leaves nothing stuck.

func scenario() -> Array:
	var game_state := autoload("GameState")
	var screen := node("%GameEndScreen")
	var panel := screen.get_node("PanelContainer")

	var x_sprite: Sprite2D = null
	for space in nodes_of_type("Space"):
		if space.coord_i == 0 and space.coord_j == 0:
			x_sprite = space.get_node("%XSprite")

	return [
		[0.00, func():
			game_state.make_move(0, 0)
			expect("sprite shows immediately", x_sprite.visible)
			# Transform2D cannot hold an exact zero scale; it stores 1e-5.
			expect("pop starts from nothing", x_sprite.scale.x < 0.01)],

		[0.05, func():
			expect_between("pop is interpolating, not snapping",
				x_sprite.scale.x, 0.01, 1.15)],

		[0.30, func():
			expect_near("pop settles at full size", x_sprite.scale.x, 1.0)],

		# X takes the top row.
		[0.35, func(): game_state.make_move(1, 0)],
		[0.40, func(): game_state.make_move(0, 1)],
		[0.45, func(): game_state.make_move(1, 1)],
		[0.50, func(): game_state.make_move(0, 2)],

		[0.55, func():
			expect("win screen is visible", screen.visible)
			expect_between("win screen is still fading in",
				screen.modulate.a, 0.0, 1.0)],

		[0.90, func():
			expect_near("win screen reaches full opacity", screen.modulate.a, 1.0)
			expect_near("panel settles at full size", panel.scale.x, 1.0)
			expect("panel pivot is centred",
				panel.pivot_offset.is_equal_approx(panel.size / 2.0))
			expect("screen blocks board clicks while shown",
				screen.mouse_filter == Control.MOUSE_FILTER_STOP)],

		[0.95, func():
			screen.play_again_requested.emit()
			expect("screen stops eating clicks the moment it starts leaving",
				screen.mouse_filter == Control.MOUSE_FILTER_IGNORE)
			expect("board clears on reset", not x_sprite.visible)
			expect("screen is still on-screen while fading out", screen.visible)],

		[1.30, func():
			expect("screen is hidden once the fade completes", not screen.visible)],

		# Reset while a pop is still running - the case that leaves a sprite
		# stuck at a fractional scale if the tween is not killed.
		[1.35, func(): game_state.make_move(0, 0)],
		[1.38, func():
			game_state.reset()
			game_state.make_move(0, 0)],
		[1.70, func():
			expect_near("replay after a mid-pop reset still settles at 1",
				x_sprite.scale.x, 1.0)
			expect("replayed sprite is visible", x_sprite.visible)],
	]
