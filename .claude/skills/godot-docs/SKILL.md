---
name: godot-docs
description: Answer Godot Engine questions using documentation matched to the exact engine version this project targets - class references, methods, signals, properties, GDScript syntax, node choice, and .tscn scene file format. Builds a local per-version cache so repeat lookups cost nothing. Use this whenever a question involves a Godot class or node, what method or signal to call, which node type fits a job, GDScript syntax, or how to hand-write a scene file - and before writing Godot code that uses an API you have not confirmed. Prefer this over recalling Godot APIs from memory, since they shift between engine versions.
when_to_use: Any question about Godot classes, nodes, methods, signals, properties, GDScript syntax, or .tscn format; before writing code against an unconfirmed API
---

# Godot Docs

Godot's API changes between releases, and the docs are versioned to match. This
project declares its engine version in `project.godot`, so answers should come
from that version's documentation - not from `/en/stable/`, and not from memory.
Recalling a method that moved or was renamed produces code that fails at parse
time and looks like a typo.

## Resolve first

```bash
uv run --script .claude/skills/godot-docs/scripts/godot_docs.py resolve GridContainer
```

```
version   : 4.7
page      : class_gridcontainer
cache_file: .../cache/4.7/class_gridcontainer.md
cached    : MISS
url       : https://docs.godotengine.org/en/4.7/classes/class_gridcontainer.html
```

This reads the project's declared version, derives the cache path and the doc
URL from it together, and reports whether the page is already cached. Deriving
both from one source is the point - a hand-built URL and a hand-built cache path
can disagree about which version they refer to, and that mistake is invisible
afterwards.

Run it with no topic to see the docs base URL and everything currently cached;
`index` lists the cache across all versions.

## Where to look, in order

**1. `references/quick-reference.md`** - GDScript syntax, node lifecycle, common
node types, and the idioms that rarely change between releases. Covers most
everyday questions with no network at all. Check here first.

**2. `references/tscn-format.md`** - the scene file format, for reading or
hand-writing `.tscn` and `.tres`.

**3. The cache** - `cached: HIT` means a previous lookup already distilled that
page. Read the file; it's authoritative for this version and free.

**4. The network** - on `MISS`, fetch the `url` the resolver printed, answer the
question, and write the distilled page into `cache_file` (the resolver has
already created the directory).

For conceptual topics rather than a specific class, search with the version
pinned: `site:docs.godotengine.org/en/4.7 <topic>`. Fetch the best result and
cache it under a descriptive slug if it's likely to come up again.

## Writing a cache entry

Cache the distilled reference, not the raw page. A dumped HTML-to-markdown
conversion is mostly navigation furniture, and re-reading it later costs nearly
as much as refetching.

Keep what a future lookup needs:

```markdown
# GridContainer (Godot 4.7)

Inherits: Container < Control < CanvasItem < Node < Object
Source: https://docs.godotengine.org/en/4.7/classes/class_gridcontainer.html

Arranges child controls in a grid, filling rows left to right.

## Properties
- `columns: int = 1` - number of columns; rows are added as needed.

## Theme constants
- `h_separation: int = 4`, `v_separation: int = 4`

## Notes
Only affects direct children that are Control nodes. Children keep their own
size flags; use `size_flags_horizontal = SIZE_EXPAND_FILL` for even columns.

## Example
...
```

Include the inheritance chain - it's how you know which inherited members are
available - and the source URL so the entry can be re-verified later. Note
version-specific behaviour explicitly; that's the whole reason the cache is
keyed by version.

Cache entries are ordinary files in the repo, so they persist across sessions
and are worth committing. A new engine version simply starts a new directory
rather than invalidating anything.

## Answering

Give the answer, then the evidence. Most questions want: what the class is for,
the two or three members that matter here, and a snippet that would actually
compile in this project.

Prefer showing the idiomatic call over describing it. When several nodes could
work, say which one fits and why - "GridContainer, because the cell count is
fixed and you want automatic row wrapping" is more useful than a list of
container types.

If the docs don't settle it - behaviour that depends on runtime state, or a
question the reference doesn't address - say so and verify with `godot-verify`
instead of inferring. A quick smoke test beats a confident guess.
