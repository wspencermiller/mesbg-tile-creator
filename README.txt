# MESBG Tile Creator

Parametric, multi-color 3D-printable stat tiles for tabletop miniatures, generated from a spreadsheet.

You describe each model in a CSV row (name plus its stat line). The tool drives [OpenSCAD](https://openscad.org/) from the command line (or a small desktop UI) and exports **one STL per color** for every row, so you can print each tile in multiple filaments.

```
┌────────────────────────────────────────────────────┐
│ ┌────────┐   MV   FV   SV   S    D    A    W    C   I │
│ │        │   6"   4    4    4    5    1    1    6   7 │
│ │  logo  │                                            │
│ │        │         Uruk-Hai Drummer                   │
│ └────────┘                                            │
│              M         W         F                    │
│              0         0         1                    │
└────────────────────────────────────────────────────┘
```

Default tile: **69 × 26 × 3 mm**, rounded corners, SVG logo on the left (20 % of the tile length), a profile row across the top, the model name (auto-sized and word-wrapped) in the middle, and an M / W / F row along the bottom.

> This is an unofficial fan tool. *Middle-earth Strategy Battle Game* and related names belong to their respective owners (Games Workshop / Middle-earth Enterprises). No affiliation or endorsement is implied.

---

## What's in the repo

| File | Purpose |
|---|---|
| `mesbg-tile-creator.scad` | The OpenSCAD model. Every setting is a variable you can edit in the Customizer or override from the command line. |
| `make_tiles.py` | Command-line batch exporter. Reads a CSV and calls OpenSCAD once per row per part. |
| `tile_ui.py` | Tkinter desktop front-end for `make_tiles.py` (file pickers, part checkboxes, progress bar, log). |
| `tiles.csv` | Example input with one row. |
| `logo.svg` *(you provide)* | Optional logo. See [Logo tips](#logo-tips). |

---

## Requirements

- **OpenSCAD**. Version **2021.01 works**, but a recent 2024+ / nightly build is strongly recommended because it supports the much faster `manifold` backend.
- **Python 3.10 or newer**. The scripts use `str | None` type hints. No third-party packages are needed.
- **tkinter** (only for the UI). It ships with Python on Windows and macOS. On some Linux distros install it separately, e.g. `sudo apt install python3-tk`.
- The **Liberation Sans Bold** font (default). It is bundled with OpenSCAD on most platforms; otherwise install it or change the `font` variable.

`make_tiles.py` looks for `openscad` on your `PATH`, then in the usual install locations on macOS and Windows. You can always point it at the executable with `--openscad`.

---

## Quick start

1. Put the files in one folder (add your `logo.svg` if you want a logo).
2. Edit `tiles.csv` (see [CSV format](#csv-format)).
3. Run:

```bash
python make_tiles.py tiles.csv --scad mesbg-tile-creator.scad --logo logo.svg --out stl_out
```

Add `--backend manifold` for much faster renders if your OpenSCAD supports it:

```bash
python make_tiles.py tiles.csv --scad mesbg-tile-creator.scad --logo logo.svg --backend manifold
```

> **Note:** `make_tiles.py` defaults to a file called `tile.scad` next to the script. If you keep the file name `mesbg-tile-creator.scad`, pass `--scad mesbg-tile-creator.scad` as above (or rename the file to `tile.scad`).

Output for each CSV row (numbered by row order):

```
stl_out/
  001_Uruk-Hai-Drummer_base.stl
  001_Uruk-Hai-Drummer_text.stl
  001_Uruk-Hai-Drummer_logo.stl     # only when --logo is given
  002_...
```

### Using the UI

```bash
python tile_ui.py
```

Pick the CSV, optional logo SVG, the `.scad` file and the output folder, tick the parts you want, and click **Run**. `tile_ui.py` must stay next to `make_tiles.py` because it imports it. It also exposes the OpenSCAD path, the backend, a dry-run mode, and a box for extra variable overrides.

### Printing the result

All parts for a tile share the same coordinates, so they line up automatically:

1. Import `base`, `text` and `logo` STLs for one tile into your slicer **together** (in PrusaSlicer/OrcaSlicer/Bambu Studio, answer **Yes** when asked whether to load them as a single object with multiple parts).
2. Assign a different filament/extruder to each part.
3. Slice and print. The default style is flush, so the top face is a single flat, multi-color surface.

---

## CSV format

A header row is required. Column names are case-insensitive and column order doesn't matter.

| Column | Meaning | Example |
|---|---|---|
| `name` | Large text on the tile, also used in the file names. Falls back to `tile` if blank. Use `\|` for a manual line break. | `Uruk-Hai Drummer` |
| `MV` | Move | `6"` |
| `FV` | Fight value | `4` |
| `SV` | Shoot value | `4+` |
| `S` | Strength | `4` |
| `D` | Defence | `5` |
| `A` | Attacks | `1` |
| `W` | Wounds | `1` |
| `C` | Courage | `6` |
| `I` | Intelligence | `7` |
| `M` | Might | `0` |
| `Will` | Will (named `Will` so it doesn't clash with `W` = Wounds) | `0` |
| `F` | Fate | `1` |

Notes:

- On the tile, `M`, `Will` and `F` appear under the headers **M W F**.
- **All stat columns must exist** in the header, even if you leave some values empty. Empty cells are allowed (you'll get a warning in the log and a blank slot on the tile).
- Values are plain text, so `4+`, `-`, `6"` or `N/A` all work. To type an inch mark in a spreadsheet, enter `6"`; CSV quoting (`"6"""`) is handled for you by Excel/Sheets.
- Extra or empty-header columns (like the blank one in the example `tiles.csv`) are ignored.
- Blank rows are skipped. Files are named by row order, so **reordering rows renumbers the output files**.
- The file is read as UTF-8 (a BOM from Excel is fine).

---

## Command-line options

```
python make_tiles.py CSV [options]
```

| Option | Description |
|---|---|
| `--logo FILE.svg` | Logo to place on every tile. Omit for no logo (the `logo` part is then skipped). |
| `--scad FILE.scad` | OpenSCAD model. Default: `tile.scad` next to the script. |
| `--out DIR` | Output folder. Default: `stl_out`. |
| `--parts base,text,logo` | Which parts to export. Default: all three. |
| `--set KEY=VALUE` | Override any OpenSCAD variable. Raw expression, repeatable. Strings need quotes. |
| `--openscad PATH` | Path to the OpenSCAD executable (auto-detected otherwise). |
| `--backend NAME` | OpenSCAD render backend, e.g. `manifold`. |
| `--timeout SECONDS` | Max time per render. Default: 600. |
| `--dry-run` | Print the OpenSCAD commands without running them. |

Examples:

```bash
# Raised text, 0.8 mm tall
python make_tiles.py tiles.csv --scad mesbg-tile-creator.scad \
    --set 'style="raised"' --set text_depth=0.8

# Only the base and text, bigger tile
python make_tiles.py tiles.csv --scad mesbg-tile-creator.scad \
    --parts base,text --set tile_length=75 --set tile_width=30

# Check what would run
python make_tiles.py tiles.csv --scad mesbg-tile-creator.scad --dry-run
```

The script exits with a non-zero status if any render failed.

---

## Customizing the design

Open `mesbg-tile-creator.scad` in OpenSCAD and use **Window → Customizer** to adjust any of these interactively, or override them with `--set` / the UI's override box.

| Group | Variable | Default | Notes |
|---|---|---|---|
| Tile | `tile_length`, `tile_width`, `tile_thickness` | 69, 26, 3 | mm |
| | `corner_radius`, `margin` | 2, 2 | `margin` is the keep-out border for all content |
| Logo | `logo_file` | `"logo.svg"` | Empty string = no logo. The batch script sets this for you. |
| | `logo_percent`, `logo_gap` | 20, 2 | Logo width as % of tile length; gap before the text block |
| Text | `font` | `Liberation Sans:style=Bold` | Any font OpenSCAD can see |
| | `header_size`, `value_size` | 3.5, 3.5 | Profile / MWF text size (auto-scaled down if the tile is short) |
| | `name_size`, `min_name_size` | 7, 2.5 | Name starts at `name_size` and shrinks to fit, but not below `min_name_size` |
| | `line_spacing`, `row_gap`, `name_gap` | 1.25, 1.5, 1.8 | Spacing tweaks |
| | `width_factor` | 0.75 | Estimated average glyph width. Raise it if text is still too wide |
| Style | `style` | `flush` | `raised` (sits on top), `flush` (inset, level with the surface), `engraved` (empty pocket) |
| | `text_depth` | 0.6 | mm |
| Multi-color | `part` | `all` | `all`, `base only`, `text only`, `logo only` (the batch script sets this per export) |
| | `base_color`, `text_color`, `logo_color` | | Preview colors only (STL files contain no color) |
| | `clearance` | 0 | Pocket gap. Use ~0.1 only if you print the pieces as loose inserts |

Variables the CSV controls (`name`, `MV` … `F`, `logo_file`, `part`) are overridden for every export, so changing their defaults in the `.scad` file only affects what you see when previewing in OpenSCAD.

---

## Logo tips

- Use a clean, single-color **SVG** with filled shapes. Strokes may not import as solid geometry, so convert strokes to outlines/paths first (Inkscape: *Path → Stroke to Path*).
- The logo is scaled to `logo_percent` of the tile length, centered vertically, and clipped to the logo area.
- The path you pass with `--logo` is converted to an absolute path, so it works from any directory.

---

## Known issues and troubleshooting

**Setup**

- **"Could not find OpenSCAD."** Install it, add it to your `PATH`, or pass `--openscad /path/to/openscad`. Linux Flatpak/AppImage installs are not auto-detected, so pass the path.
- **`OpenSCAD file not found: .../tile.scad`.** The script's default model name is `tile.scad`. Use `--scad mesbg-tile-creator.scad` or rename the file. (The UI already defaults to `mesbg-tile-creator.scad`.)
- **`TypeError` / syntax error on `str | None`.** Your Python is older than 3.10.
- **`--backend` fails.** The option only exists in recent OpenSCAD builds. The 2021.01 release doesn't support it; leave the backend blank there.

**Rendering**

- **Slow renders.** Text and SVG import are expensive with the default CGAL backend. Use `--backend manifold` on a recent build, and consider exporting only the parts you need. The per-render timeout is 600 s by default (adjust with `--timeout`; the UI uses a fixed 600 s).
- **Text looks too wide, too narrow or overflows its column.** Layout uses an *estimate* of text width, not real font metrics. Tune `width_factor`, or change `font` to one with similar widths. If the configured font isn't installed, OpenSCAD silently substitutes another, which changes widths.
- **Very long names** shrink down to `min_name_size` and then may be clipped by the text area. Use a `|` for a manual line break, shorten the name, or lower `min_name_size`.
- **Non-Latin characters** require a font that contains those glyphs. File names are ASCII-only: any other character is replaced by `-`, and a name with no ASCII characters becomes `tile` (the row number prefix keeps files unique).
- **Logo missing or warning about `logo.svg`.** Opening the `.scad` file directly in OpenSCAD with the default `logo_file = "logo.svg"` needs that file next to it. Set `logo_file = ""` for no logo. The batch script handles this automatically via `--logo`.
- **`engraved` style produces no text/logo STLs.** In that style the text and logo are empty pockets in the base, so there's nothing to export for those parts. The script logs them as "nothing to export (empty geometry)" and counts them as skipped, not failed. This detection relies on OpenSCAD's "empty" warning wording, so a differently worded message from a future version could show up as a failure instead.
- **Thin gaps or z-fighting in the slicer** when using `flush` with `clearance = 0`. The pieces touch exactly; that's intended for a single multi-part object. Only add `clearance` (~0.1) if you print the pieces separately as inserts.

**Quoting**

- Strings passed to `--set` need their own quotes, and your shell may need another layer: `--set 'style="raised"'` on bash/zsh. In Windows PowerShell or cmd the quoting differs (for example `--set style=\"raised\"`). If in doubt, use `--dry-run` to inspect the exact command, or use the UI's override box, where you type `style="raised"` with no extra escaping.
- Values containing a double quote (like `6"`) are escaped automatically, but if OpenSCAD receives a mangled value on Windows, run with `--dry-run` and test the command by hand.

**Windows/macOS/Linux**

- On macOS, the Python from python.org includes tkinter; Homebrew's Python may need `brew install python-tk`.

---

## Contributing

Issues and pull requests are welcome. Useful areas: automatic text-width measurement, 3MF export with colors, and an option to place several tiles on one build plate.

## License

Add a license of your choice (for example MIT) as a `LICENSE` file and mention it here.