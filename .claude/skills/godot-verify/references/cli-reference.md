# Godot CLI Reference

Options beyond what `godot_verify.py` wraps. Source: the [Godot command line
tutorial](https://docs.godotengine.org/en/4.7/tutorials/editor/command_line_tutorial.html).

**Contents:** [Ground rules](#ground-rules) · [Running](#running-a-project) ·
[Validation](#validation) · [Export](#export) · [Video capture](#video-capture) ·
[Test suites](#running-test-suites) · [Docs generation](#documentation-generation) ·
[Migration](#project-migration) · [Traps](#traps-worth-remembering) ·
[Autoloads](#autoloads-and---check-only) · [Driving scenes](#driving-a-live-scene) ·
[Class cache](#the-global-class-cache) · [Rendering a frame](#rendering-a-frame)

## Ground rules

`--path <dir>` must point at the directory containing `project.godot`. Script
paths passed to `--script` are resource paths *relative to the project*, so
`scripts/board.gd`, not an absolute filesystem path.

`--headless` sets the display driver to headless and audio to Dummy. Required on
any machine without a GPU or display, and it is what makes a run safe to invoke
from an agent - a windowed run blocks until a human closes the window.

**Never run a windowed Godot from a tool call.** `godot --path .` with no
`--quit-after` waits forever. Always bound it with `--headless --quit-after N`,
or run it in the background if you genuinely need the window.

## Running a project

```bash
godot --headless --path . --quit-after 5          # boot 5 frames, then exit
godot --headless --path . res://scenes/board.tscn --quit-after 5
godot --path . --debug                            # local stdout debugger (windowed)
godot --profiling                                 # script profiler
godot --gpu-profile                               # per-frame GPU task breakdown
```

`--quit-after 0` disables the limit, i.e. runs forever. Use a positive number.

## Validation

```bash
godot --headless --check-only --script scripts/board.gd --path .
```

Exits 1 on failure, 0 when clean.

**`--script` is mandatory.** The whole-project form does nothing: `godot
--headless --check-only --path .` aborts with *"Couldn't detect whether to run
the editor, the project manager or a specific project"* and exits 1 having parsed
no files at all. That exit code is indistinguishable from a genuine failure,
which is why validation must loop over files one at a time.

Catches parse errors *and* static type errors: bad assignments, unknown methods
on typed bases, wrong argument counts. It does not catch anything that only
happens at runtime - null nodes, missing scene paths, bad signal wiring. Those
need a `smoke` run.

## Export

Requires two things that do not exist by default: an `export_presets.cfg` with a
matching preset (created in the editor under Project > Export), and installed
export templates for the engine version (Editor > Manage Export Templates).
Missing either produces a failure that is easy to misread as a code problem.

```bash
godot --headless --path . --export-release "Windows Desktop" ./builds/game.exe
godot --headless --path . --export-debug   "Windows Desktop" ./builds/game_debug.exe
godot --headless --path . --export-pack    "Windows Desktop" ./builds/game.pck
godot --headless --path . --export-patch   "Windows Desktop" ./builds/patch.pck
```

- `--export-release` - optimised production build.
- `--export-debug` - debug template, includes the remote debugger. Implies `--import`.
- `--export-pack` - data package only (`.pck`/`.zip`), no executable.
- `--export-patch` - only files changed since a previous build.

The preset name must match the `name=` field in `export_presets.cfg` exactly,
quoting included.

## Video capture

Renders deterministically to a file rather than in realtime, so it works on a
machine with no display and does not depend on framerate.

```bash
godot --headless --path . --write-movie output.avi --quit-after 300
godot --path . --write-movie output.avi --resolution 1920x1080 --quit-after 600
```

Useful for confirming a visual change actually looks right instead of asking a
human to look. 300 frames is ~5 seconds at 60fps.

## Running test suites

Neither framework ships with Godot; both are project add-ons.

**GUT:**
```bash
godot --headless --path . -s res://addons/gut/gut_cmdln.gd \
      -gdir=res://tests -ginclude_subdirs -gexit
```

**gdUnit4:** ships a CLI runner that emits JUnit XML and HTML reports. See the
[gdUnit4 docs](https://github.com/godot-gdunit-labs/gdUnit4) for current flags.

Check whether `addons/gut` or `addons/gdUnit4` exists before assuming either is
available.

## Documentation generation

```bash
godot --doctool ./docs                 # full engine API reference
godot --gdscript-docs res://scripts    # API docs from your own ## docstrings
```

## Project migration

```bash
godot --validate-conversion-3to4       # report what would change
godot --convert-3to4                   # apply it (rewrites files in place)
```

Validate before converting.

## Traps worth remembering

**Exit codes lie on runtime errors.** A `--quit-after` run returns 0 even after
the game throws. Scan stdout for `SCRIPT ERROR:` / `ERROR:` instead.

**Version mismatches pass silently.** An older engine checking a newer project
exits 0 with no warning. Always confirm the binary matches `config/features`.

**On Windows, prefer the `_console.exe` build.** Official Windows releases ship
both; the plain `.exe` can detach from the console and write nothing to stdout,
which is indistinguishable from a clean run.

**Windows installs nest.** The official archive unpacks to a *directory* named
`Godot_v4.7.1-stable_win64.exe` containing the actual executable, so a flat glob
for `Godot.exe` finds nothing on a normal install.

**`--import` starts the editor.** It implies `--editor` and `--quit`. Harmless,
but it is slower than the other commands and needs a longer timeout.

## Autoloads and `--check-only`

`--check-only` never instantiates autoload singletons, so **any** script
referencing one fails with `Compile Error: Identifier not found: <Name>` even
though the project boots fine. Only statically foldable members - consts and
enums - resolve.

Verified against 4.7.1 by bisecting to a minimal two-file project. The plausible
explanations are all wrong: `uid://` versus `res://` autoload paths behave
identically, so does a stale, absent, or freshly rebuilt `.godot` uid cache, and
so does `--editor`. No flag fixes it.

`check` therefore reads the `[autoload]` section of `project.godot` and reports
these files as `ok*`. That filter is safe because of *when* the engine gives up:

- Genuine mistakes are **parse/analyser** errors, which abort before the compile
  stage is ever reached. A file with a real bug reports that bug and never gets
  as far as the autoload error - so autoload noise appears *only* when nothing
  else is wrong.
- A real unknown identifier reads differently anyway - `Identifier "Foo" not
  declared in the current scope` - and is never filtered.

The one residual blind spot is a second, genuine unknown identifier later in a
file whose autoload reference came first. `smoke` covers that case.

## Driving a live scene

`--script` runs any script that `extends SceneTree` (or `MainLoop`), which is how
`drive` boots a scene and steps it forward. It is also the fastest way to settle
an API question the docs leave ambiguous:

```bash
godot --headless --quit-after 600 --script res://probe.gd
```

Verified against 4.7.1 while building `drive`:

**Autoload identifiers are not in scope under `--script`.** `GameState` fails to
compile with `Identifier not found` even though `/root/GameState` exists and the
same code works when the project boots normally. Reach the node instead:
`root.get_node_or_null("GameState")`.

**`--fixed-fps N` is mandatory for observing anything mid-flight.** Headless runs
the loop unthrottled, and the deltas are large and uneven — a 0.15s tween
completed inside a single frame, so a sample taken "part-way through" returned
the final value. An assertion like `scale < 1.1` then passes on a tween that
never ran. With `--fixed-fps 60` the same sample read `0.758`.

**Never `await` inside a `--script` MainLoop.** An awaited `process_frame` or
`SceneTree.create_timer()` that never resolves hangs the process with no output
at all; killing it leaves an empty log indistinguishable from an instant crash.
Drive state from `_process(delta) -> bool` instead — returning `true` quits.

**`_initialize()` and `_process(delta) -> bool` both work** on a `SceneTree`
subclass, and `add_child()` fires `_ready()` synchronously, so nodes and
`%UniqueNames` are reachable immediately after the scene is added.

**Sampling two steps in one frame reads pre-delta state.** If a scenario fires
step *n* and step *n+1* in the same frame, nothing has advanced between them.
Cap it at one step per frame.

**`Node2D.scale = Vector2.ZERO` stores as `(1e-5, 1e-5)`** — `Transform2D` cannot
represent an exact zero scale. Assert `< 0.01`, never `== 0`.

## The global class cache

`class_name` declarations resolve through
`.godot/global_script_class_cache.cfg`, written by an import pass and normally
gitignored. Without it, `extends SomeClass` fails with `Could not find base class
"SomeClass"` and typed references fail with `Could not find type "X"` — in code
that is perfectly correct. A fresh clone therefore reports a pile of parse errors
until `godot --headless --import --path .` has run once.

Two files declaring the same `class_name` is a hard error: `Class "X" hides a
global script class`. This bites when tooling keeps a template copy inside the
project — store such templates under a non-`.gd` extension so the engine never
registers them.

## Rendering a frame

Verified against 4.7.1 while building `shot`:

**`--headless` cannot produce pixels at all.** It installs the *dummy*
rendering server, so `get_viewport().get_texture().get_image()` returns null and
the engine logs `Parameter "t" is null` from
`servers/rendering/dummy/storage/texture_storage.h`. No flag overrides it —
the rasteriser is chosen by the display driver. Every headless command therefore
verifies a game that was never drawn.

**A windowed run still exits on its own if it is bounded.** The rule against
launching a windowed Godot from a tool call is narrower than "never": what hangs
forever is a windowed run *with no frame budget*. With `--quit-after` it opens a
window, renders, and terminates unattended with exit 0:

```bash
godot --path . --fixed-fps 60 --quit-after 120 --script res://tests/shot.gd
```

That is the only way to obtain a screenshot, so forbidding windowed runs
outright costs the only pixel evidence available. It does require a display —
on a truly headless machine there is no workaround.

**`Image.save_png()` accepts both `res://` paths and absolute OS paths**, so a
capture can be written outside the project without going through
`ProjectSettings.globalize_path()`.

**Sample a captured frame before trusting it.** A frame that never drew still
saves as a valid PNG — uniformly one colour. Counting distinct colours across a
coarse grid distinguishes "rendered" from "wrote a blank buffer"; without that
check a screenshot step passes on a black image.
