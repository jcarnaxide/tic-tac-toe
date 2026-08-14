# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

A Godot 4.7 tic-tac-toe game (Mobile renderer), plus three project-local skills
for working on Godot codebases.

## Verifying changes

There is no test suite — no `addons/`, no GUT or gdUnit4. Verification is the
engine itself, via the `godot-verify` skill's script:

```bash
# Parse + static type check the whole project (cheap; run on every edit)
uv run --script .claude/skills/godot-verify/scripts/godot_verify.py check

# One file
uv run --script .claude/skills/godot-verify/scripts/godot_verify.py check scripts/game_state.gd

# Boot headless and report runtime errors
uv run --script .claude/skills/godot-verify/scripts/godot_verify.py smoke

# Drive a live scene at a fixed timestep - the only thing that tests animation
uv run --script .claude/skills/godot-verify/scripts/godot_verify.py drive tests/animation.gd

# Which engine binary will be used, and why
uv run --script .claude/skills/godot-verify/scripts/godot_verify.py find
```

Run Python through `uv run --script`, never a bare `python`/`python3` — the
scripts declare their deps via PEP 723 inline metadata.

**`check` reports `ok*` for `main.gd` and `space.gd`.** `--check-only` cannot
instantiate autoloads, so any *call* into `GameState` is unresolvable — those two
parse clean but their singleton usage is unproven. `game_end_screen.gd` escapes
this only because `GameState.PLAYER.X` is an enum, and consts/enums fold
statically. `ok*` is not a failure; it also is not proof. Only `smoke` exercises
autoload usage for real.

**Never launch a windowed Godot from a tool call** — it blocks until a human
closes the window. Always `--headless --quit-after N`.

**Neither `check` nor `smoke` tests anything animated.** `smoke` boots the scene
and never clicks it, so every tween is unexercised while both commands report
clean. `tests/animation.gd` is the scenario that actually covers the piece pop
and the win-screen transition; run `drive` after touching either.

## Architecture

`GameState` (`scripts/game_state.gd`, autoloaded) is the single source of truth.
`_board` is the only place board state lives — **nothing else stores it**, and
nodes must not cache or shadow it.

Data flows one direction each way:

- **Input up:** a `Space`'s `ClickArea` calls `GameState.make_move(i, j)` and
  stops there. It does not decide whether the move is legal or what to draw.
  `make_move` validates internally, so callers must not pre-check.
- **Render down:** `GameState` emits `board_changed(i, j, player)` and
  `board_reset`. Each `Space` listens, ignores coordinates that aren't its own,
  and sets sprite visibility. Rendering is derived state, never assigned by the
  caller that triggered the move.
- **Game over:** `GameState.game_over(winner)` → `main.gd` → `GameEndScreen.set_winner()`,
  where `winner == null` means a tie.

Transitions belong to whichever node draws the thing. `Space` pops its own sprite
in; `GameEndScreen` exposes `appear()`/`dismiss()` rather than being shown and
hidden by `main.gd`, so `main` says *when* and the screen decides *how*.
`GameState` knows nothing about any of it.

### Landmines

**`PLAYER.X` is 0.** `_check_winner()` returns `null` or a `PLAYER`, so its result
must be tested with `!= null`. Writing `if winner:` silently drops every win by X
— that was a real bug here. The null check is load-bearing, not defensive.

**Signals are connected in `_ready()`, never in the editor.** All three
connections previously lived in `.tscn` files and were deliberately moved into
GDScript; wire new ones the same way. Beyond keeping them greppable, a `.tscn`
connection stores the emitting node's *full path* — `PlayAgainButton` was welded
to a six-level container layout — and a typo'd method name there fails at runtime
behind a completely green `check`, whereas in code the analyser catches it.

When a node is only reachable by a deep path, mark it `unique_name_in_owner` and
reach it with `%Name` instead of spelling the path out.

**Tweens need a kill-before-start.** A retriggerable tween must
`if _tween and _tween.is_valid(): _tween.kill()` first — the docs warn against
two tweens on one property, and `is_valid()` is the check that matters because a
finished tween goes invalid while the reference stays live. `_on_board_reset()`
kills too, or a pop still running writes `scale` after the board has cleared.

**A `Control` scales from its top-left corner.** `pivot_offset` defaults to
`(0, 0)`, and `size` is not settled during `_ready()` — the end screen's panel
measures 396×309 at runtime, not the 396×136 its `.tscn` offsets suggest. Track
it via the `resized` signal instead of reading `size` once. Relatedly,
`mouse_filter` defaults to `MOUSE_FILTER_STOP`, so a full-rect Control keeps
eating clicks aimed at the board underneath for as long as it is visible —
including throughout a fade-out. `dismiss()` switches to `IGNORE` for that reason.

**The 3×3 shape is hardcoded in three places** — `SIZE` and `CONSECUTIVES` in
`game_state.gd`, and nine hand-placed `Space` instances in `main.tscn` each
carrying exported `coord_i`/`coord_j`. No code generates the grid. Changing board
size means editing the scene too.

**`project.godot` references the main scene and the `GameState` autoload by
`uid://`**, resolved through `.godot/uid_cache.bin`, which is gitignored. A fresh
clone or a copied project directory has no cache, so `GameState` resolves to
`Nil` until you run the script's `import` command once.

## Skills

Three project-local skills, split by the question being asked:

- **`godot-docs`** — "how do I do X?" Version-pinned docs with a committed cache.
- **`godot-verify`** — "does it actually work?" Runs the engine. Evidence, not opinion.
- **`godot-review`** — "is it any good?" Prioritises correctness and architecture
  over style.
