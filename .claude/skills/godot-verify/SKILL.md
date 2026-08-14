---
name: godot-verify
description: Verify a Godot project actually works by running the engine headlessly - parse-check GDScript for syntax and type errors, boot the game to catch runtime errors, and export builds without opening the editor. Use this whenever you have written or changed a .gd or .tscn file and want to know if it really works, when the user asks to check for errors, validate, test, run, smoke-test, build, or export the project, or before claiming any Godot change is complete. Prefer this over reasoning about whether code looks correct - the engine is the only authority on whether it parses and boots.
when_to_use: After writing or editing any GDScript or scene file; when asked to check for errors, run the project, or export a build; before reporting Godot work as done
---

# Godot Verify

Every other Godot skill produces an *opinion*. This one produces *evidence* -
the engine either parses the code or it doesn't, boots or it doesn't. Reach for
it whenever a claim about Godot code needs to be true rather than plausible.

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

Four CLI behaviours fail *silently* toward false confidence. The script absorbs
them; hand-rolling these commands means rediscovering each the hard way.

- **`--check-only` is inert without `--script`** - it aborts having parsed
  nothing and exits 1, which reads exactly like "your code is broken." `check`
  loops per file instead.
- **A mismatched engine version passes silently** - 4.2 checking a 4.7 project
  exits 0 with no warning. The script matches the binary to `config/features`.
- **A clean exit code does not mean the game ran** - `--quit-after` returns 0
  even when `_ready()` threw. `smoke` judges by output, not status.
- **`--check-only` cannot resolve autoloads** - every script touching a
  singleton reports `Identifier not found`, however sound the code. `check`
  reports those as `ok*` rather than failures.

`references/cli-reference.md` has the evidence, the exact failure text, and why
filtering the autoload case does not hide real bugs.

## Typical loop

After changing GDScript:

```bash
uv run --script .claude/skills/godot-verify/scripts/godot_verify.py check
```

`check` catches more than syntax - the analyser resolves types statically, so it
also reports bad assignments and unknown method calls. Cheap; run it on every
edit.

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
message. Both `check` and `smoke` preserve `at:` context lines and backtraces for
exactly this reason - "it failed" without a location just makes the reader run it
again themselves.

`ok*` means clean apart from autoload references `check` structurally cannot
resolve: parsed, but its autoload calls are unproven. Don't report these as
failures; don't claim their autoload usage is verified either. `smoke` settles it.

On a version-mismatch warning, treat a clean result as **unverified** rather than
passing, and say so. A wrong-version green looks like confirmation, which makes
it worse than no result.

## When something is genuinely missing

Setup problems, not bad code - report these plainly rather than working around
them:

- **No binary found** - pass `--godot <path>`, or ask where Godot is installed.
- **No `run/main_scene`** - `smoke` has nothing to boot. Use `--scene`, or note
  that the project needs a main scene set in Project Settings.
- **No `export_presets.cfg`** - presets are created in the editor under
  Project > Export; the CLI can only use ones that already exist.
- **Export produces no file** - almost always missing export templates, added
  via Editor > Manage Export Templates.

## Beyond these commands

The CLI also records gameplay to video (`--write-movie`), generates docs from
docstrings (`--gdscript-docs`), and runs GUT or gdUnit4 suites headlessly.
`references/cli-reference.md` has the exact invocations.
