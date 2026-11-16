#!/usr/bin/env python3
"""
Batch-generate multi-color tile STLs from a CSV by driving the OpenSCAD CLI.

For every CSV row it exports up to three STLs (one per color/filament):
    <NNN>_<name>_base.stl
    <NNN>_<name>_text.stl
    <NNN>_<name>_logo.stl     (only when --logo is given)

CSV columns (header row required, names are case-insensitive):
    name   shown large on the tile; also used in the file names (falls back to "tile")
           use | for a manual line break
    MV     Move value, e.g. 8"  (inch mark is part of the notation)
    FV     Fight value, e.g. 8
    SV     Shoot value, e.g. 4+
    S      Strength, e.g. 6
    D      Defence, e.g. 8
    A      Attacks, e.g. 3
    W      Wounds, e.g. 3
    C      Courage, e.g. 3+
    I      Intelligence, e.g. 3+
    M      Might, e.g. 3
    Will   Will, e.g. 3   (named Will so it does not clash with Wounds = W)
    F      Fate, e.g. 3

On the tile, M / Will / F display under headers M W F.

Example:
    python make_tiles.py tiles.csv --logo logo.svg --out stl_out
    python make_tiles.py tiles.csv --set 'style="raised"' --set text_depth=0.8
"""

import argparse
import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

# short part name -> value of the `part` variable in tile.scad
PARTS = {"base": "base only", "text": "text only", "logo": "logo only"}

FALLBACK_PATHS = [
    "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
    "/Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD",
    r"C:\Program Files\OpenSCAD\openscad.exe",
    r"C:\Program Files\OpenSCAD (Nightly)\openscad.exe",
]

# OpenSCAD variables / CSV headers for all stat columns
STAT_KEYS = ("MV", "FV", "SV", "S", "D", "A", "W", "C", "I", "M", "Will", "F")


def scad_str(value: str) -> str:
    """Quote a Python string as an OpenSCAD string literal."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def find_openscad(explicit: str | None) -> str:
    if explicit:
        return explicit
    found = shutil.which("openscad")
    if found:
        return found
    for candidate in FALLBACK_PATHS:
        if Path(candidate).exists():
            return candidate
    sys.exit("Could not find OpenSCAD. Install it or pass --openscad /path/to/openscad")


def slugify(text: str, maxlen: int = 40) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")[:maxlen].strip("-")
    return slug or "tile"


def read_rows(csv_path: Path):
    """Yield (line_no, name, stat_values) for each data row.

    stat_values is a dict mapping STAT_KEYS -> string.
    """
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            sys.exit(f"{csv_path} is empty")
        fields = {name.strip().lower(): name for name in reader.fieldnames}

        missing = [k for k in STAT_KEYS if k.lower() not in fields]
        if missing:
            sys.exit(
                "CSV needs these columns: "
                + ", ".join(STAT_KEYS)
                + f"\nMissing: {', '.join(missing)}"
            )

        for line_no, row in enumerate(reader, start=2):
            if not any((v or "").strip() for v in row.values()):
                continue  # skip blank lines

            stat_values = {
                key: (row[fields[key.lower()]] or "").strip()
                for key in STAT_KEYS
            }

            name = ""
            if "name" in fields:
                name = (row[fields["name"]] or "").strip()
            name = name.replace("\r\n", "|").replace("\n", "|")

            yield line_no, name or "tile", stat_values


def build_command(exe, scad, out_file, overrides, backend):
    cmd = [exe, "-o", str(out_file)]
    if backend:
        cmd += ["--backend", backend]
    for key, value in overrides.items():
        cmd += ["-D", f"{key}={value}"]
    cmd.append(str(scad))
    return cmd


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path, help="CSV with MV/FV/SV/.../M/Will/F values")
    ap.add_argument("--logo", type=Path, help="SVG logo file (omit for no logo)")
    ap.add_argument("--scad", type=Path, default=Path(__file__).with_name("tile.scad"),
                    help="the OpenSCAD tile file (default: tile.scad next to this script)")
    ap.add_argument("--out", type=Path, default=Path("stl_out"), help="output folder (default: stl_out)")
    ap.add_argument("--parts", default="base,text,logo",
                    help="comma-separated parts to export (default: base,text,logo)")
    ap.add_argument("--set", dest="extra", action="append", default=[], metavar="KEY=VALUE",
                    help="extra OpenSCAD variable override, raw expression; repeatable. "
                         "Strings need quotes, e.g. --set 'style=\"raised\"' --set text_depth=0.8")
    ap.add_argument("--openscad", help="path to the OpenSCAD executable (auto-detected by default)")
    ap.add_argument("--backend", help="OpenSCAD render backend, e.g. manifold (much faster on 2024+ builds)")
    ap.add_argument("--timeout", type=int, default=600, help="seconds allowed per render (default: 600)")
    ap.add_argument("--dry-run", action="store_true", help="print the commands without running them")
    args = ap.parse_args()

    if not args.scad.exists():
        sys.exit(f"OpenSCAD file not found: {args.scad}")
    if not args.csv.exists():
        sys.exit(f"CSV not found: {args.csv}")
    if args.logo and not args.logo.exists():
        sys.exit(f"Logo not found: {args.logo}")

    parts = [p.strip() for p in args.parts.split(",") if p.strip()]
    bad = [p for p in parts if p not in PARTS]
    if bad:
        sys.exit(f"Unknown part(s): {', '.join(bad)} (choose from {', '.join(PARTS)})")
    if not args.logo:
        parts = [p for p in parts if p != "logo"]

    extra = {}
    for item in args.extra:
        if "=" not in item:
            sys.exit(f"--set expects KEY=VALUE, got: {item}")
        key, value = item.split("=", 1)
        extra[key.strip()] = value.strip()

    exe = args.openscad or ("openscad" if args.dry_run else find_openscad(None))
    args.out.mkdir(parents=True, exist_ok=True)

    # absolute path so it resolves no matter where OpenSCAD is launched from
    logo_value = scad_str(str(args.logo.resolve())) if args.logo else '""'

    ok, skipped, failed = 0, 0, 0
    rows = list(read_rows(args.csv))
    if not rows:
        sys.exit("No data rows found in the CSV")

    for index, (line_no, name, stat_values) in enumerate(rows, start=1):
        blank = [k for k, v in stat_values.items() if v == ""]
        if blank:
            print(f"  ! line {line_no}: empty column(s): {', '.join(blank)}")

        print(f"[{index}/{len(rows)}] {name}")
        stem = f"{index:03d}_{slugify(name)}"

        for part in parts:
            out_file = args.out / f"{stem}_{part}.stl"
            overrides = {
                "name": scad_str(name),
                **{key: scad_str(value) for key, value in stat_values.items()},
                "logo_file": logo_value,
                "part": scad_str(PARTS[part]),
                **extra,
            }
            cmd = build_command(exe, args.scad, out_file, overrides, args.backend)

            if args.dry_run:
                print("   ", " ".join(f"'{c}'" if " " in c else c for c in cmd))
                continue

            out_file.unlink(missing_ok=True)
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
            except subprocess.TimeoutExpired:
                print(f"   x {part}: timed out after {args.timeout}s")
                failed += 1
                continue

            if out_file.exists() and out_file.stat().st_size > 0:
                print(f"   + {out_file.name}")
                ok += 1
            elif "empty" in (result.stderr or "").lower() and result.returncode == 0:
                # e.g. engraved style has no text/logo piece
                print(f"   - {part}: nothing to export (empty geometry)")
                skipped += 1
            else:
                print(f"   x {part}: OpenSCAD failed (exit {result.returncode})")
                tail = (result.stderr or "").strip().splitlines()[-5:]
                for line in tail:
                    print(f"       {line}")
                failed += 1

    if not args.dry_run:
        print(f"\nDone: {ok} exported, {skipped} skipped, {failed} failed -> {args.out.resolve()}")
        sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
