---
name: godot-verify
description: Verify a Godot project actually works by running the engine headlessly - parse-check GDScript for syntax and type errors, boot the game to catch runtime errors, and export builds without opening the editor. Use this whenever you have written or changed a .gd or .tscn file and want to know if it really works, when the user asks to check for errors, validate, test, run, smoke-test, build, or export the project, or before claiming any Godot change is complete. Prefer this over reasoning about whether code looks correct - the engine is the only authority on whether it parses and boots.
when_to_use: After writing or editing any GDScript or scene file; when asked to check for errors, run the project, or export a build; before reporting Godot work as done
---

# Godot Verify

Every other Godot skill produces an *opinion*. This one produces *evidence*: the
engine either parses the code or it doesn't, boots the scene or it doesn't.
Reach for it whenever a claim about Godot code needs to be true rather than
plausible.

## Use the bundled script

```bash
uv run --script .claude/skills/godot-verify/scripts/godot_verify.py <command>
```

Run it from anywhere in the project - it walks up to find `project.godot`. Add
`--project <dir>` to target a different project.

| Command | What it does |
|---|---|
| `find` | Show which engine binary will be used, and why |
| `check [paths...]` | Parse-check GDScript. No paths = whole project |
| `smoke [--frames N] [--scene res://...]` | Boot headless, report runtime errors |
| `import` | Reimport resources (after adding assets) |
| `presets` | List export presets |
| `export --preset NAME --output PATH [--debug]` | Build without the editor |

All commands exit non-zero on failure, so they chain safely.

## Why the script instead of raw commands

Three CLI behaviours are counter-intuitive, and each one fails *silently* in the
direction of false confidence. The script exists to absorb them. Hand-rolling
these commands means rediscovering all three the hard way.

**`--check-only` does nothing without `--script`.** The docs say "use with
--script" and mean it literally. Run `godot --headless --check-only --path .`
and the engine aborts with *"Couldn't detect whether to run the editor, the
project manager or a specific project"* and exits 1, having parsed nothing. That
exit 1 looks exactly like "your code has errors." Validation has to loop over
files one at a time, which is what `check` does.

**A mismatched engine version passes silently.** Godot 4.2 checking a 4.7
project exits 0 with no warning at all. Since a machine can hold many engine
versions at once, "whichever binary I found first" is a real risk. The script
reads `config/features` from `project.godot` and matches the binary to it,
warning loudly if it can't.

**A clean exit code does not mean the game ran.** `--quit-after` runs return 0
even when the game threw during `_ready()`. The error is on stdout with a
backtrace, but the status code says success. `smoke` ignores the exit code and
judges by output instead.

## Typical loop

After changing GDScript:

```bash
uv run --script .claude/skills/godot-verify/scripts/godot_verify.py check
```

`check` catches more than syntax - GDScript's analyser resolves types statically,
so it also reports `Cannot assign a value of type "String" as "int"` and
`Function "no_such_method()" not found in base self`. Cheap and worth running on
every edit.

Once it parses, confirm it actually boots:

```bash
uv run --script .claude/skills/godot-verify/scripts/godot_verify.py smoke
```

This is where wiring mistakes surface - null nodes, bad `$Path` lookups, signals
connected to methods that don't exist. `check` cannot see any of those, so a
green `check` alone is not evidence the game works.

Boot a specific scene with `--scene res://scenes/board.tscn` when the project has
no main scene set, or when you only want to exercise one piece.

## Reading the results

Report failures with the file and line the engine gave you, and quote the
message. Both `check` and `smoke` preserve the `at:` context lines and
backtraces for exactly this reason - "it failed" without a location just forces
the reader to run it again themselves.

If the script warns about a version mismatch, treat a clean result as
**unverified** rather than passing, and say so. A wrong-version green is worse
than no result, because it looks like confirmation.

## When something is genuinely missing

Errors that mean setup, not bad code - report these plainly rather than working
around them:

- **No binary found** - pass `--godot <path>`, or ask where Godot is installed.
- **No `run/main_scene`** - `smoke` has nothing to boot. Use `--scene`, or note
  that the project needs a main scene set in Project Settings.
- **No `export_presets.cfg`** - presets are created in the editor under
  Project > Export. The CLI can only use presets that already exist.
- **Export produces no file** - almost always missing export templates for that
  engine version, installed via Editor > Manage Export Templates.

## Beyond these commands

The engine CLI does considerably more - recording gameplay to video with
`--write-movie`, generating docs from docstrings with `--gdscript-docs`,
running GUT or gdUnit4 test suites headlessly. See `references/cli-reference.md`
for the options worth knowing and the exact invocations.
