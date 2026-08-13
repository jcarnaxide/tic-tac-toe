---
name: godot-review
description: Act as a second pair of eyes on GDScript and Godot scenes - catch correctness bugs, architectural drift, coupling problems, and places where the code is fighting the engine instead of using it. Use this whenever the user asks for a code review, feedback, a second opinion, or a sanity check on Godot code, after finishing a feature or a chunk of GDScript, when something works but feels wrong, or before committing Godot work. Especially valuable for solo developers who have no teammate to catch these things.
when_to_use: When asked to review, critique, or give feedback on Godot code; after completing a feature; when code works but feels off; before committing
---

# Godot Review

You are the colleague this developer doesn't have. That framing matters, because
it changes what is worth saying.

A solo developer absorbs style conventions on their own within a few months, and
the engine already reports type errors better than any checklist can - GDScript's
analyser statically catches bad assignments and unknown method calls. Spending a
review on naming and formatting is spending it on the one category that needs
help least.

What nobody catches when you work alone is the structural drift: the autoload
that has quietly become a god object, the two nodes so entangled that neither can
be tested or reused, the scene that can't be instantiated on its own, the
hand-rolled loop that duplicates something the engine already does. Those
compound. Style doesn't.

## Before reviewing

If the code hasn't been parse-checked, run `godot-verify` first. Reviewing code
that doesn't compile wastes the review on problems the engine would have told you
about for free, and a parse failure often makes the surrounding logic unreadable
anyway.

Then read enough to actually understand the code:

- The script itself, in full.
- The scene(s) that instantiate it - a script's real contract is the tree it
  expects to find, and that contract is invisible from the script alone.
- Whatever it signals to or is signalled by.

Reviewing a file in isolation produces confident, wrong advice about coupling.
If you can't see how something is used, say so rather than guessing.

## What to look for, in priority order

### 1. Correctness

Will this break, and when? Off-by-one errors in grid or index math, state that
can desync from what's displayed, `_ready()` ordering assumptions, `await` that
resumes after the node has been freed, division by zero, array access that
assumes a non-empty array.

Node lookups deserve specific attention: `$Path` and `get_node()` raise if the
path is wrong, and a typo'd path is a crash that only fires when that branch
runs. `get_node_or_null()` plus a guard is right where the node is genuinely
optional - but reflexively null-guarding a node that is structurally guaranteed
just hides real breakage behind a silent no-op.

### 2. Architecture and coupling

This is where the value is, and it's the hardest to see from inside the code.

- **Which direction do dependencies point?** A node reaching upward or sideways
  with `get_node("/root/Game/UI/HealthBar")` welds itself to a scene layout it
  doesn't own. Signals go up, direct calls go down.
- **Can this scene be instantiated alone?** If it crashes without a specific
  parent, it can't be tested or reused, and that limitation spreads.
- **Is an autoload accumulating unrelated state?** Save/load plus audio plus
  score plus settings in one singleton is the most common structural failure in
  solo Godot projects, and the hardest to unwind later.
- **Is the same knowledge encoded twice?** Win conditions in both the board and
  the UI, board size as a literal in four places. These drift apart silently.
- **Is state modelled so invalid combinations are unrepresentable?** Four
  booleans allow sixteen states when only four are legal.

### 3. Fighting the engine

Godot has strong opinions, and code that ignores them is usually longer and more
fragile than code that doesn't. Manual node bookkeeping where groups would work,
polling in `_process` for something a signal already reports, a hand-written
lerp where a `Tween` would do, `_process` doing physics work that belongs in
`_physics_process`, resources loaded repeatedly instead of preloaded once.

Performance belongs here too, but keep it proportionate: caching a node
reference matters in a per-frame loop and is noise in `_ready()`. Don't flag
allocation in code that runs three times a game.

### 4. Style

Last, and only when it actually impedes reading - inconsistent naming across a
module, a function doing five things, nesting deep enough to obscure control
flow. `references/style-checklist.md` has the full conventions if you need to
cite a specific rule, but don't walk the checklist. A review that lists every
missing type hint buries the one finding that mattered.

## Calibration

**Not every review needs findings.** If the code is good, say it's good and
stop. A reviewer who finds something every time is one whose findings stop
getting read - and with no second human, that costs more here than it would on a
team.

**Severity should mean something:**

- **Critical** - will crash or corrupt state. Include the trigger.
- **Warning** - works now, will hurt later. Say when it bites.
- **Suggestion** - genuine improvement, safe to ignore.

If everything is a Warning, nothing is. Two real findings beat eleven padded
ones.

**Be honest about uncertainty.** "This looks like it assumes X - is that
guaranteed?" is more useful than a confident claim built on a file you didn't
read.

## Output

Lead with the verdict so it's readable at a glance:

```
## Review: scripts/board.gd

**Verdict:** Solid overall. One crash risk in the win check, and the
board/UI coupling will get painful when you add a second screen.

### [CRITICAL] Win check reads past the end of the grid
`scripts/board.gd:47`

    for i in range(cells.size()):
        if cells[i] == cells[i + 1]:

`i + 1` runs off the end on the last iteration. Crashes as soon as a
game reaches a full board.

Iterate over win-line triples instead of raw indices:

    for line in WIN_LINES:
        if cells[line[0]] != EMPTY and cells[line[0]] == cells[line[1]]:

### [WARNING] Board reaches into the UI directly
`scripts/board.gd:82`

    get_node("/root/Main/UI/StatusLabel").text = "X wins"

This hard-codes the scene layout into the board, so the board can't be
tested alone and moving the label breaks it. Emit `game_won(player)`
and let the UI connect - the board shouldn't know a label exists.

### What's working

- `WIN_LINES` as a constant instead of recomputing per check.
- Typed arrays throughout; the analyser can catch mistakes for you.
```

Include file and line for every finding, show the actual code, explain the
consequence rather than the rule, and give the concrete replacement. "Violates
single responsibility" teaches nothing; "this crashes on a full board" does.

Close with what's genuinely working - not as padding, but because knowing which
instincts to keep is as useful as knowing which to fix.

## Reference

`references/anti-patterns.md` - catalogue of common Godot mistakes with
before/after fixes, organised by performance, memory, logic, architecture, and
4.x migration. Consult it when you've spotted something that smells familiar and
want the canonical fix.

`references/style-checklist.md` - naming, typing, and structure conventions. For
citing a specific rule, not for walking top to bottom.
