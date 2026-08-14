# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Compose the game's art from Kenney's CC0 asset packs.

    uv run --script tools/build_art.py

Writes assets/background.png, assets/x.png and assets/o.png, and prints the
Space positions for scenes/main.tscn. The board geometry and those positions
come from the same constants, so the pieces cannot drift off the tiles - edit
CELL or GAP here and re-run rather than nudging coordinates in the editor.

Source packs are downloaded once into .art-cache/ (gitignored). The URLs carry
a content hash, so they pin an exact revision of each pack; if one 404s, find
the new link on the pack's page at kenney.nl/assets.

Run `godot_verify.py import` afterwards - Godot only picks up new image data
once it has regenerated the .import files.
"""
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".art-cache"
ASSETS = ROOT / "assets"

PACKS = {
    "game-icons": "https://kenney.nl/media/pages/assets/game-icons/1ebf9c14af-1677661579/kenney_game-icons.zip",
    "board-game-icons": "https://kenney.nl/media/pages/assets/board-game-icons/19cae04050-1721645690/kenney_board-game-icons.zip",
    "ui-pack": "https://kenney.nl/media/pages/assets/ui-pack/f651646eab-1718203990/kenney_ui-pack.zip",
}

W, H = 1152, 648
CELL, GAP = 168, 18
GLYPH = 104                       # glyph box inside a cell
BACKDROP = (44, 95, 141, 255)     # deep blue
X_COLOUR = (232, 56, 79, 255)     # Kenney red
O_COLOUR = (255, 195, 0, 255)     # Kenney amber

TILE = "ui-pack/PNG/Grey/Double/button_square_flat.png"
SOURCES = (
    ("x", "game-icons/PNG/White/2x/cross.png", X_COLOUR),
    ("o", "board-game-icons/PNG/Double (128px)/flip_empty.png", O_COLOUR),
)


def fetch(name: str, url: str) -> Path:
    """Download and unzip a pack once; return its extracted directory."""
    target = CACHE / name
    if target.is_dir():
        return target
    print(f"  downloading {name}...")
    CACHE.mkdir(exist_ok=True)
    with urllib.request.urlopen(url, timeout=180) as response:
        blob = response.read()
    zipfile.ZipFile(io.BytesIO(blob)).extractall(target)
    # Every Kenney pack ships its licence; its absence means we grabbed
    # something other than what we think we did.
    if not any(target.rglob("[Ll]icense.txt")):
        raise SystemExit(f"{name}: no licence file in the archive - refusing to use it")
    return target


def tint(img: Image.Image, colour) -> Image.Image:
    """Recolour a white-on-transparent icon, preserving its alpha."""
    solid = Image.new("RGBA", img.size, colour)
    solid.putalpha(img.getchannel("A"))
    return solid


def glyph(path: Path, colour) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    im = im.crop(im.getbbox())        # source icons carry uneven padding
    im.thumbnail((GLYPH, GLYPH), Image.LANCZOS)
    canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    canvas.alpha_composite(im, ((128 - im.width) // 2, (128 - im.height) // 2))
    return tint(canvas, colour)


def main() -> None:
    print("Sources:")
    for name, url in PACKS.items():
        fetch(name, url)
    print(f"  cached in {CACHE.relative_to(ROOT)}")

    board = 3 * CELL + 2 * GAP
    ox, oy = (W - board) // 2, (H - board) // 2

    tile = Image.open(CACHE / TILE).convert("RGBA").resize((CELL, CELL), Image.LANCZOS)
    bg = Image.new("RGBA", (W, H), BACKDROP)
    centres = []
    for i in range(3):
        for j in range(3):
            bg.alpha_composite(tile, (ox + j * (CELL + GAP), oy + i * (CELL + GAP)))
        centres.append([(ox + j * (CELL + GAP) + CELL // 2,
                         oy + i * (CELL + GAP) + CELL // 2) for j in range(3)])
    bg.convert("RGB").save(ASSETS / "background.png")

    for name, src, colour in SOURCES:
        glyph(CACHE / src, colour).save(ASSETS / f"{name}.png")

    print(f"\nWrote background.png ({W}x{H}), x.png, o.png (128x128) to assets/")
    print(f"Board {board}px at ({ox},{oy}), cell {CELL}, gap {GAP}.")
    print("\nSpace positions for scenes/main.tscn:")
    for i, row in enumerate(centres):
        for j, (cx, cy) in enumerate(row):
            print(f"  coord_i={i} coord_j={j}  position = Vector2({cx}, {cy})")


if __name__ == "__main__":
    sys.exit(main())
