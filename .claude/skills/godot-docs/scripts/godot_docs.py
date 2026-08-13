# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Resolve Godot doc URLs and cache paths for the version this project targets.

The docs are versioned and the APIs genuinely differ between releases, so
answering from `/en/stable/` risks describing a class the project cannot use.
This reads the version the project actually declares and derives everything from
that, so the URL and the cache location can never disagree about which release
is being documented.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DOCS_HOST = "https://docs.godotengine.org"


def find_project_root(start: Path) -> Path:
    cur = start.resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / "project.godot").is_file():
            return candidate
    sys.exit(
        f"error: no project.godot found in {start} or any parent.\n"
        "       Pass --project <dir> pointing at the Godot project root."
    )


def project_version(root: Path) -> str | None:
    """Read the version from config/features, e.g. '4.7'.

    Godot writes config/features=PackedStringArray("4.7", "Mobile") - the
    version is the numeric entry, the rest are renderer/platform tags.
    """
    text = (root / "project.godot").read_text(encoding="utf-8", errors="replace")
    match = re.search(r"config/features\s*=\s*PackedStringArray\(([^)]*)\)", text)
    if not match:
        return None
    for entry in re.findall(r'"([^"]+)"', match.group(1)):
        if re.fullmatch(r"\d+(\.\d+)*", entry):
            return entry
    return None


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def cache_dir(version: str) -> Path:
    return skill_root() / "cache" / version


def slug(class_name: str) -> str:
    """Class reference pages lowercase the whole name: Node2D -> class_node2d."""
    return "class_" + re.sub(r"[^A-Za-z0-9]", "", class_name).lower()


def cmd_resolve(root: Path, args) -> int:
    version = project_version(root)
    if not version:
        print(
            "warning: project.godot declares no version in config/features.\n"
            "         Falling back to 'stable', which may not match this project.",
            file=sys.stderr,
        )
        version = "stable"

    cdir = cache_dir(version)
    print(f"version   : {version}")
    print(f"cache_dir : {cdir}")

    if not args.topic:
        print(f"docs_base : {DOCS_HOST}/en/{version}/")
        cached = sorted(p.stem for p in cdir.glob("*.md")) if cdir.is_dir() else []
        print(f"cached    : {len(cached)} page(s)")
        for name in cached:
            print(f"  {name}")
        return 0

    name = slug(args.topic)
    path = cdir / f"{name}.md"
    print(f"page      : {name}")
    print(f"cache_file: {path}")
    print(f"cached    : {'HIT' if path.is_file() else 'MISS'}")
    print(f"url       : {DOCS_HOST}/en/{version}/classes/{name}.html")
    if not path.is_file():
        # The writer needs the directory to exist; creating it here keeps the
        # caller from having to think about it.
        cdir.mkdir(parents=True, exist_ok=True)
    return 0


def cmd_index(root: Path, args) -> int:
    """Summarise every cached version, so stale caches are visible."""
    base = skill_root() / "cache"
    if not base.is_dir():
        print("No cache yet.")
        return 0
    payload = {}
    for vdir in sorted(base.iterdir()):
        if vdir.is_dir():
            payload[vdir.name] = sorted(p.stem for p in vdir.glob("*.md"))
    if not payload:
        print("No cache yet.")
        return 0
    print(json.dumps(payload, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        prog="godot_docs",
        description="Resolve version-correct Godot doc URLs and cache paths.",
    )
    p.add_argument("--project", default=".", help="project directory (default: cwd)")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("resolve", help="resolve a class/topic to a URL and cache path")
    r.add_argument("topic", nargs="?", help="class name, e.g. GridContainer")
    r.set_defaults(func=cmd_resolve)

    i = sub.add_parser("index", help="list everything cached, by version")
    i.set_defaults(func=cmd_index)

    args = p.parse_args()
    return args.func(find_project_root(Path(args.project)), args)


if __name__ == "__main__":
    sys.exit(main())
