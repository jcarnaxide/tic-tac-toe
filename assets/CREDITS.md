# Art credits

Every source asset is **CC0 1.0** (public domain) by [Kenney](https://kenney.nl).
CC0 waives the attribution requirement; Kenney asks for credit voluntarily, and
recording provenance here means a future change can find the originals again.

`assets/background.png`, `x.png` and `o.png` are not hand-edited. They are
composed from the packs below by `tools/build_art.py` - change that script and
re-run it rather than editing the PNGs.

| Output | Source pack | File within the pack |
|---|---|---|
| `x.png` | [Game Icons](https://kenney.nl/assets/game-icons) | `PNG/White/2x/cross.png` |
| `o.png` | [Board Game Icons](https://kenney.nl/assets/board-game-icons) | `PNG/Double (128px)/flip_empty.png` |
| `background.png` | [UI Pack](https://kenney.nl/assets/ui-pack) | `PNG/Grey/Double/button_square_flat.png` |

The glyphs ship white-on-transparent and are tinted at build time - red
`#E8384F` for X, amber `#FFC300` for O - so the two players differ by colour as
well as by shape.

The pack URLs in `build_art.py` contain a content hash and therefore pin an
exact revision. If one stops resolving, the current link is on the pack's page
at [kenney.nl/assets](https://kenney.nl/assets).
