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
