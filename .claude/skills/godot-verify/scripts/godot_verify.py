# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Locate the right Godot binary for a project and run verification against it.

Why this exists: three things about the Godot CLI are easy to get wrong, and all
three fail *quietly* — which is the worst way to fail when an agent is trusting
the result.

  1. `--check-only` does nothing without `--script`. Run it with only `--path`
     and Godot aborts with "Couldn't detect whether to run the editor..." and
     exits 1 — having parsed nothing. Exit 1 then reads as "your code is broken"
     when it actually means "your command was broken". Validation must loop
     over files one at a time.

  2. A mismatched engine version passes silently. Godot 4.2 checking a 4.7
     project exits 0 with no warning. Green, and meaningless. So we parse
     `config/features` from project.godot and match the binary to it.

  3. The headless smoke run exits 0 even when the game throws at runtime. The
     error appears on stdout with a backtrace, but the exit code says success.
     Anything chaining on `&&` or `|| exit 1` reports a broken game as fine.
     So we scan output text and derive our own exit status.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")

# Lines matching these mean real problems worth surfacing.
ERROR_MARKERS = (
    "SCRIPT ERROR:",
    "USER ERROR:",
    "ERROR:",
    "Parse Error:",
    "CRASH:",
)

# Headless mode has no GPU or audio device, so it narrates that fact. None of
# this indicates a problem with the project, and leaving it in trains whoever
# reads the output to skim past real errors sitting next to it.
BENIGN = (
    "Your video card drivers seem not to support",
    "Unable to initialize Vulkan",
    "Detected GPU has no support",
    "audio driver Dummy",
    "No audio driver",
    "Using \"dummy\" audio driver",
    "Cannot initialize the display server",
    "DisplayServer headless",
)


def strip_ansi(text: str) -> str:
    return ANSI.sub("", text)


# --------------------------------------------------------------------------
# Project discovery
# --------------------------------------------------------------------------

def find_project_root(start: Path) -> Path:
    """Walk upward looking for project.godot so the tool works from subdirs."""
    cur = start.resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / "project.godot").is_file():
            return candidate
    sys.exit(
        f"error: no project.godot found in {start} or any parent directory.\n"
        "       Pass --project <dir> pointing at the Godot project root."
    )


def project_version(root: Path) -> str | None:
    """Read the engine version the project declares, e.g. '4.7'.

    Godot writes this as config/features=PackedStringArray("4.7", "Mobile") —
    the version is the entry that looks like a number, the rest are tags like
    "Mobile" or "Forward Plus".
    """
    text = (root / "project.godot").read_text(encoding="utf-8", errors="replace")
    match = re.search(r"config/features\s*=\s*PackedStringArray\(([^)]*)\)", text)
    if not match:
        return None
    for entry in re.findall(r'"([^"]+)"', match.group(1)):
        if re.fullmatch(r"\d+(\.\d+)*", entry):
            return entry
    return None


def main_scene(root: Path) -> str | None:
    text = (root / "project.godot").read_text(encoding="utf-8", errors="replace")
    match = re.search(r'run/main_scene\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else None


# --------------------------------------------------------------------------
# Engine discovery
# --------------------------------------------------------------------------

def candidate_paths() -> list[Path]:
    """Every plausible Godot binary location, before version filtering.

    Windows installs are the awkward case: the official build unpacks into a
    *directory* named Godot_v4.7.1-stable_win64.exe which then contains the
    real .exe, so a flat glob for "Godot.exe" finds nothing on a perfectly
    normal install. Recursive globbing handles both layouts.
    """
    system = platform.system()
    found: list[Path] = []

    def add_glob(base: Path, pattern: str) -> None:
        if base.is_dir():
            found.extend(p for p in base.rglob(pattern) if p.is_file())

    if system == "Windows":
        program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        program_files_x86 = Path(
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        )
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        for base in (
            program_files / "Godot",
            local / "Godot",
            local / "Programs" / "Godot",
            program_files_x86 / "Steam/steamapps/common/Godot Engine",
            Path.home() / "scoop/apps/godot",
            Path.home() / "scoop/apps/godot4",
        ):
            add_glob(base, "*.exe")
    elif system == "Darwin":
        for base in (Path("/Applications"), Path.home() / "Applications"):
            add_glob(base, "Godot")
        found.extend(
            p for p in (Path("/opt/homebrew/bin/godot"), Path("/usr/local/bin/godot"))
            if p.is_file()
        )
    else:
        for p in (
            Path.home() / ".local/bin/godot",
            Path("/usr/bin/godot"),
            Path("/usr/local/bin/godot"),
            Path("/usr/bin/godot4"),
        ):
            if p.is_file():
                found.append(p)
        add_glob(Path.home() / ".local/share/godot", "Godot*")

    # Anything already on PATH.
    for name in ("godot", "godot4", "Godot"):
        from shutil import which

        hit = which(name)
        if hit:
            found.append(Path(hit))

    # Keep only things that actually look like the engine. Without this filter a
    # Godot install directory can hand back unrelated tools (a formatter, an
    # uninstaller) that would then fail confusingly at --version time.
    def looks_like_godot(p: Path) -> bool:
        stem = p.name.lower()
        return stem.startswith("godot") or stem == "godot"

    unique: dict[str, Path] = {}
    for p in found:
        if looks_like_godot(p):
            unique.setdefault(str(p).lower(), p)
    return list(unique.values())


def cache_file() -> Path:
    return Path(tempfile.gettempdir()) / "godot-verify-versions.json"


def load_cache() -> dict:
    try:
        return json.loads(cache_file().read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_cache(cache: dict) -> None:
    try:
        cache_file().write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception:
        pass  # A cold cache is slow, not broken — never fail the run over it.


def binary_version(exe: Path, cache: dict) -> str | None:
    """Ask a binary its version, memoized on (path, mtime).

    Probing costs ~1s per binary and a machine can easily hold a dozen engine
    versions, so an uncached `find` would dominate the runtime of every check.
    """
    try:
        key = f"{exe}|{exe.stat().st_mtime_ns}"
    except OSError:
        return None
    if key in cache:
        return cache[key]
    try:
        out = subprocess.run(
            [str(exe), "--version"],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    version = strip_ansi(out.stdout + out.stderr).strip().splitlines()
    value = version[-1].strip() if version else None
    cache[key] = value
    return value


def version_tuple(version: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", version.split("-")[0])
    return tuple(int(n) for n in nums[:3])


def prefer_console(exe: Path) -> Path:
    """On Windows, favour the _console.exe sibling when one exists.

    The plain .exe detaches from the console on some Windows shells and writes
    nothing to stdout, which looks exactly like "no errors" — a silent false
    pass. The console build always writes to the attached stream.
    """
    if platform.system() != "Windows":
        return exe
    console = exe.with_name(exe.stem + "_console" + exe.suffix)
    return console if console.is_file() else exe


def select_engine(root: Path, explicit: str | None) -> tuple[Path, str, list[str]]:
    """Return (binary, version, warnings), matching the project's version."""
    warnings: list[str] = []
    if explicit:
        exe = Path(explicit)
        if not exe.is_file():
            sys.exit(f"error: --godot path does not exist: {exe}")
        cache = load_cache()
        return prefer_console(exe), binary_version(exe, cache) or "unknown", warnings

    cache = load_cache()
    candidates: list[tuple[Path, str]] = []
    for exe in candidate_paths():
        version = binary_version(exe, cache)
        if version and version[0].isdigit():
            candidates.append((exe, version))
    save_cache(cache)

    if not candidates:
        sys.exit(
            "error: no Godot binary found.\n"
            "       Checked PATH and the usual install locations.\n"
            "       Pass --godot <path-to-executable> to point at it directly."
        )

    wanted = project_version(root)
    if wanted:
        want_mm = version_tuple(wanted)[:2]
        matches = [c for c in candidates if version_tuple(c[1])[:2] == want_mm]
        if matches:
            best = max(matches, key=lambda c: version_tuple(c[1]))
            return prefer_console(best[0]), best[1], warnings
        best = max(candidates, key=lambda c: version_tuple(c[1]))
        warnings.append(
            f"project.godot declares Godot {wanted}, but no {wanted}.x binary was "
            f"found. Falling back to {best[1]}.\n"
            "  A mismatched engine reports success on code it cannot actually run, "
            "so treat a clean result here as unverified."
        )
        return prefer_console(best[0]), best[1], warnings

    best = max(candidates, key=lambda c: version_tuple(c[1]))
    warnings.append(
        "project.godot declares no config/features version; using the newest "
        f"binary found ({best[1]})."
    )
    return prefer_console(best[0]), best[1], warnings


# --------------------------------------------------------------------------
# Output classification
# --------------------------------------------------------------------------

def extract_errors(output: str) -> list[str]:
    """Pull real error blocks out of engine output, dropping headless noise.

    Godot follows an error line with indented "   at: ..." context and often a
    backtrace. Those continuation lines carry the file and line number, so they
    are kept with their parent — reporting the message without the location
    would force whoever reads this to go re-run it themselves.
    """
    blocks: list[str] = []
    current: list[str] | None = None
    for raw in strip_ansi(output).splitlines():
        line = raw.rstrip()
        if any(marker in line for marker in ERROR_MARKERS):
            if any(noise in line for noise in BENIGN):
                current = None
                continue
            current = [line]
            blocks.append("\n".join(current))
            continue
        if current is not None and (line.startswith((" ", "\t"))) and line.strip():
            blocks[-1] += "\n" + line
            continue
        current = None
    return blocks


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def gdscript_files(root: Path, targets: list[str]) -> list[Path]:
    if targets:
        out: list[Path] = []
        for t in targets:
            p = Path(t)
            p = p if p.is_absolute() else root / p
            if p.is_dir():
                out.extend(sorted(p.rglob("*.gd")))
            elif p.is_file():
                out.append(p)
            else:
                sys.exit(f"error: no such file or directory: {t}")
        return out
    # `.godot/` is the engine's own import cache, and addons/ is third-party
    # code the project did not write — neither belongs in a project's own
    # error report.
    return sorted(
        p for p in root.rglob("*.gd")
        if ".godot" not in p.parts and "addons" not in p.parts
    )


def cmd_find(root: Path, args) -> int:
    exe, version, warnings = select_engine(root, args.godot)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    declared = project_version(root) or "unspecified"
    print(f"project     : {root}")
    print(f"declares    : Godot {declared}")
    print(f"using       : {version}")
    print(f"binary      : {exe}")
    return 0


def cmd_check(root: Path, args) -> int:
    """Parse-check each script individually.

    Per-file is not a stylistic choice: `--check-only` is a no-op without
    `--script`, so a single whole-project invocation cannot work. Running one
    file at a time also means a broken script does not mask the ones after it.
    """
    exe, version, warnings = select_engine(root, args.godot)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)

    files = gdscript_files(root, args.paths)
    if not files:
        print("No .gd files found - nothing to check.")
        return 0

    print(f"Checking {len(files)} script(s) with Godot {version}\n")
    failed: list[tuple[Path, str]] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        try:
            proc = subprocess.run(
                [str(exe), "--headless", "--check-only",
                 "--script", rel, "--path", str(root)],
                capture_output=True, text=True, timeout=args.timeout,
            )
        except subprocess.TimeoutExpired:
            failed.append((path, f"timed out after {args.timeout}s"))
            print(f"  TIMEOUT  {rel}")
            continue

        errors = extract_errors(proc.stdout + proc.stderr)
        if proc.returncode != 0 or errors:
            detail = "\n".join(errors) or (proc.stdout + proc.stderr).strip()
            failed.append((path, detail))
            print(f"  FAIL     {rel}")
        else:
            print(f"  ok       {rel}")

    if failed:
        print(f"\n{len(failed)} of {len(files)} script(s) failed:\n")
        for path, detail in failed:
            print(f"--- {path.relative_to(root).as_posix()} ---")
            print(detail)
            print()
        return 1

    print(f"\nAll {len(files)} script(s) parsed cleanly.")
    return 0


def cmd_smoke(root: Path, args) -> int:
    """Boot the project headless for a few frames and report anything it threw.

    Godot exits 0 here even after a runtime error, so the exit code is ignored
    on purpose and the verdict comes from the output text instead.
    """
    exe, version, warnings = select_engine(root, args.godot)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)

    scene = args.scene or main_scene(root)
    if not scene:
        print(
            "error: the project sets no run/main_scene and no --scene was given.\n"
            "       Nothing to boot. Set a main scene in Project Settings, or\n"
            "       pass --scene res://path/to/scene.tscn.",
            file=sys.stderr,
        )
        return 2

    cmd = [str(exe), "--headless", "--path", str(root),
           "--quit-after", str(args.frames)]
    if args.scene:
        cmd.append(args.scene)

    print(f"Booting {scene} headless for {args.frames} frame(s) "
          f"with Godot {version}\n")
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=args.timeout
        )
    except subprocess.TimeoutExpired:
        print(
            f"error: still running after {args.timeout}s and was killed.\n"
            "       A headless run bounded by --quit-after should exit promptly;\n"
            "       this usually means the project blocked during startup.",
            file=sys.stderr,
        )
        return 1

    combined = proc.stdout + proc.stderr
    body = strip_ansi(combined).strip()
    if body:
        print(body)
        print()

    errors = extract_errors(combined)
    if errors:
        print(f"FAILED - {len(errors)} runtime error(s) during boot:\n")
        for block in errors:
            print(block)
            print()
        return 1

    print("Booted cleanly - no runtime errors.")
    return 0


def cmd_presets(root: Path, args) -> int:
    cfg = root / "export_presets.cfg"
    if not cfg.is_file():
        print(
            "No export_presets.cfg in this project.\n"
            "Export presets are created in the editor (Project > Export...), and\n"
            "the CLI can only use presets that already exist.",
        )
        return 1
    text = cfg.read_text(encoding="utf-8", errors="replace")
    names = re.findall(r'^name\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not names:
        print("export_presets.cfg exists but defines no presets.")
        return 1
    print("Available export presets:")
    for n in names:
        print(f"  {n}")
    return 0


def cmd_export(root: Path, args) -> int:
    exe, version, warnings = select_engine(root, args.godot)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)

    if not (root / "export_presets.cfg").is_file():
        print(
            "error: no export_presets.cfg — there is nothing to export with.\n"
            "       Create a preset in the editor under Project > Export...",
            file=sys.stderr,
        )
        return 2

    out = Path(args.output)
    out = out if out.is_absolute() else (root / out)
    out.parent.mkdir(parents=True, exist_ok=True)

    mode = "--export-debug" if args.debug else "--export-release"
    cmd = [str(exe), "--headless", "--path", str(root),
           mode, args.preset, str(out)]
    print(f"Exporting preset {args.preset!r} -> {out} (Godot {version})\n")
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=args.timeout
        )
    except subprocess.TimeoutExpired:
        print(f"error: export timed out after {args.timeout}s", file=sys.stderr)
        return 1

    body = strip_ansi(proc.stdout + proc.stderr).strip()
    if body:
        print(body)
        print()

    errors = extract_errors(proc.stdout + proc.stderr)
    if proc.returncode != 0 or errors or not out.exists():
        print("Export FAILED.", file=sys.stderr)
        for block in errors:
            print(block, file=sys.stderr)
        if not out.exists():
            print(
                "       No output file was produced. The usual cause is missing\n"
                "       export templates for this engine version — install them\n"
                "       via Editor > Manage Export Templates.",
                file=sys.stderr,
            )
        return 1

    size = out.stat().st_size
    print(f"Export OK - {out} ({size:,} bytes)")
    return 0


def cmd_import(root: Path, args) -> int:
    """Reimport resources so newly added assets resolve before other commands."""
    exe, version, warnings = select_engine(root, args.godot)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    print(f"Importing resources with Godot {version}...")
    try:
        proc = subprocess.run(
            [str(exe), "--headless", "--import", "--path", str(root)],
            capture_output=True, text=True, timeout=args.timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"error: import timed out after {args.timeout}s", file=sys.stderr)
        return 1
    errors = extract_errors(proc.stdout + proc.stderr)
    if errors:
        print("Import reported errors:\n", file=sys.stderr)
        for block in errors:
            print(block, file=sys.stderr)
        return 1
    print("Import complete.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="godot_verify",
        description="Locate the project's Godot version and verify the project with it.",
    )
    p.add_argument("--project", default=".", help="project directory (default: cwd)")
    p.add_argument("--godot", help="explicit path to a Godot binary")
    sub = p.add_subparsers(dest="command", required=True)

    f = sub.add_parser("find", help="show which Godot binary will be used")
    f.set_defaults(func=cmd_find)

    c = sub.add_parser("check", help="parse-check GDScript (syntax AND type errors)")
    c.add_argument("paths", nargs="*", help="files or dirs (default: whole project)")
    c.add_argument("--timeout", type=int, default=120)
    c.set_defaults(func=cmd_check)

    s = sub.add_parser("smoke", help="boot headless for N frames, report runtime errors")
    s.add_argument("--frames", type=int, default=5)
    s.add_argument("--scene", help="scene to boot instead of the main scene")
    s.add_argument("--timeout", type=int, default=120)
    s.set_defaults(func=cmd_smoke)

    i = sub.add_parser("import", help="reimport resources")
    i.add_argument("--timeout", type=int, default=300)
    i.set_defaults(func=cmd_import)

    pr = sub.add_parser("presets", help="list export presets")
    pr.set_defaults(func=cmd_presets)

    e = sub.add_parser("export", help="export a build using an existing preset")
    e.add_argument("--preset", required=True)
    e.add_argument("--output", required=True)
    e.add_argument("--debug", action="store_true")
    e.add_argument("--timeout", type=int, default=600)
    e.set_defaults(func=cmd_export)

    return p


def main() -> int:
    args = build_parser().parse_args()
    root = find_project_root(Path(args.project))
    return args.func(root, args)


if __name__ == "__main__":
    sys.exit(main())
