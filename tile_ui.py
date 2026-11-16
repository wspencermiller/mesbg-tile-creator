#!/usr/bin/env python3
"""
A small desktop UI for make_tiles.py.

Pick your CSV, (optional) logo SVG, the tile.scad file, and an output folder,
then click Run. Needs no extra packages — tkinter ships with Python.

Keep this file next to make_tiles.py.
"""

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_tiles as mt  # noqa: E402  (reuses read_rows / build_command / etc.)

PART_LABELS = {"base": "Base", "text": "Text", "logo": "Logo"}


class TileApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tile Batch Exporter")
        self.geometry("720x620")
        self.minsize(640, 520)

        self.csv_path = tk.StringVar()
        self.logo_path = tk.StringVar()
        self.scad_path = tk.StringVar(value=str(Path(__file__).with_name("mesbg-tile-creator.scad")))
        self.out_dir = tk.StringVar(value=str(Path(__file__).with_name("stl_out")))
        self.openscad_path = tk.StringVar()
        self.backend = tk.StringVar()
        self.part_vars = {p: tk.BooleanVar(value=True) for p in PART_LABELS}
        self.dry_run = tk.BooleanVar(value=False)

        self.log_queue: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None

        self._build_ui()
        self.after(100, self._poll_queue)

    # ---------------------------------------------------------- layout ----
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        files = ttk.LabelFrame(self, text="Files")
        files.pack(fill="x", padx=10, pady=8)
        files.columnconfigure(1, weight=1)

        self._file_row(files, 0, "CSV (stats / MWF):", self.csv_path,
                       lambda: self._pick_file(self.csv_path, [("CSV files", "*.csv")]))
        self._file_row(files, 1, "Logo SVG (optional):", self.logo_path,
                       lambda: self._pick_file(self.logo_path, [("SVG files", "*.svg")]),
                       clearable=True)
        self._file_row(files, 2, "tile.scad file:", self.scad_path,
                       lambda: self._pick_file(self.scad_path, [("OpenSCAD files", "*.scad")]))
        self._file_row(files, 3, "Output folder:", self.out_dir,
                       lambda: self._pick_dir(self.out_dir))

        opts = ttk.LabelFrame(self, text="Options")
        opts.pack(fill="x", padx=10, pady=4)

        parts_row = ttk.Frame(opts)
        parts_row.pack(fill="x", **pad)
        ttk.Label(parts_row, text="Parts to export:").pack(side="left")
        for key, label in PART_LABELS.items():
            ttk.Checkbutton(parts_row, text=label, variable=self.part_vars[key]).pack(side="left", padx=6)

        adv = ttk.Frame(opts)
        adv.pack(fill="x", **pad)
        adv.columnconfigure(1, weight=1)
        ttk.Label(adv, text="OpenSCAD path (blank = auto-detect):").grid(row=0, column=0, sticky="w")
        ttk.Entry(adv, textvariable=self.openscad_path).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Label(adv, text="Backend (e.g. manifold, blank = default):").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(adv, textvariable=self.backend).grid(row=1, column=1, sticky="ew", padx=6, pady=(4, 0))

        ttk.Checkbutton(opts, text="Dry run (print commands, don't render)",
                        variable=self.dry_run).pack(anchor="w", **pad)

        ttk.Label(self, text="Extra variable overrides (one per line, KEY=VALUE — "
                              'quote strings, e.g. style="raised")').pack(anchor="w", padx=10)
        self.extra_text = tk.Text(self, height=4)
        self.extra_text.pack(fill="x", padx=10, pady=(0, 8))

        btn_row = ttk.Frame(self)
        btn_row.pack(fill="x", padx=10)
        self.run_btn = ttk.Button(btn_row, text="Run", command=self._on_run)
        self.run_btn.pack(side="left")
        ttk.Button(btn_row, text="Open output folder", command=self._open_out_dir).pack(side="left", padx=6)

        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=(8, 4))

        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_box = tk.Text(log_frame, state="disabled", wrap="word", font=("Courier", 10))
        scroll = ttk.Scrollbar(log_frame, command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=scroll.set)
        self.log_box.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _file_row(self, parent, row, label, var, command, clearable=False):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", padx=4)
        ttk.Button(parent, text="Browse...", command=command).grid(row=row, column=2, padx=4)
        if clearable:
            ttk.Button(parent, text="Clear", command=lambda: var.set("")).grid(row=row, column=3, padx=(0, 8))

    # -------------------------------------------------------- file pickers
    def _pick_file(self, var, filetypes):
        path = filedialog.askopenfilename(filetypes=filetypes + [("All files", "*.*")])
        if path:
            var.set(path)

    def _pick_dir(self, var):
        path = filedialog.askdirectory()
        if path:
            var.set(path)

    def _open_out_dir(self):
        out = Path(self.out_dir.get())
        out.mkdir(parents=True, exist_ok=True)
        if sys.platform == "darwin":
            subprocess.run(["open", str(out)])
        elif sys.platform.startswith("win"):
            subprocess.run(["explorer", str(out)])
        else:
            subprocess.run(["xdg-open", str(out)])

    # ------------------------------------------------------------- run ---
    def _log(self, line: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _on_run(self):
        if self.worker and self.worker.is_alive():
            return

        csv_path = Path(self.csv_path.get())
        scad_path = Path(self.scad_path.get())
        out_dir = Path(self.out_dir.get())
        logo = Path(self.logo_path.get()) if self.logo_path.get().strip() else None

        if not csv_path.exists():
            messagebox.showerror("Missing file", f"CSV not found:\n{csv_path}")
            return
        if not scad_path.exists():
            messagebox.showerror("Missing file", f"tile.scad not found:\n{scad_path}")
            return
        if logo and not logo.exists():
            messagebox.showerror("Missing file", f"Logo not found:\n{logo}")
            return

        parts = [p for p, v in self.part_vars.items() if v.get()]
        if not parts:
            messagebox.showerror("No parts selected", "Select at least one part to export.")
            return

        extra = {}
        for raw in self.extra_text.get("1.0", "end").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            if "=" not in raw:
                messagebox.showerror("Bad override", f"Expected KEY=VALUE, got:\n{raw}")
                return
            key, value = raw.split("=", 1)
            extra[key.strip()] = value.strip()

        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.run_btn.configure(state="disabled")
        self.progress.configure(value=0)

        self.worker = threading.Thread(
            target=self._run_job,
            args=(csv_path, scad_path, out_dir, logo, parts, extra,
                  self.openscad_path.get().strip() or None,
                  self.backend.get().strip() or None,
                  self.dry_run.get()),
            daemon=True,
        )
        self.worker.start()

    def _run_job(self, csv_path, scad_path, out_dir, logo, parts, extra, openscad, backend, dry_run):
        q = self.log_queue
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            exe = openscad or (None if dry_run else mt.find_openscad(None))
            logo_value = mt.scad_str(str(logo.resolve())) if logo else '""'

            rows = list(mt.read_rows(csv_path))
            if not rows:
                q.put(("error", "No data rows found in the CSV"))
                q.put(("done", None))
                return

            q.put(("max", len(rows) * len(parts)))
            ok = skipped = failed = 0
            done = 0

            for index, (line_no, name, stat_values) in enumerate(rows, start=1):
                blank = [k for k, v in stat_values.items() if v == ""]
                if blank:
                    q.put(("log", f"  ! line {line_no}: empty column(s): {', '.join(blank)}"))

                q.put(("log", f"[{index}/{len(rows)}] {name}"))
                stem = f"{index:03d}_{mt.slugify(name)}"

                for part in parts:
                    out_file = out_dir / f"{stem}_{part}.stl"
                    overrides = {
                        "name": mt.scad_str(name),
                        **{key: mt.scad_str(value) for key, value in stat_values.items()},
                        "logo_file": logo_value,
                        "part": mt.scad_str(mt.PARTS[part]),
                        **extra,
                    }
                    cmd = mt.build_command(exe or "openscad", scad_path, out_file, overrides, backend)

                    if dry_run:
                        q.put(("log", "    " + " ".join(f"'{c}'" if " " in c else c for c in cmd)))
                        done += 1
                        q.put(("progress", done))
                        continue

                    out_file.unlink(missing_ok=True)
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                    except subprocess.TimeoutExpired:
                        q.put(("log", f"   x {part}: timed out"))
                        failed += 1
                        done += 1
                        q.put(("progress", done))
                        continue

                    if out_file.exists() and out_file.stat().st_size > 0:
                        q.put(("log", f"   + {out_file.name}"))
                        ok += 1
                    elif "empty" in (result.stderr or "").lower() and result.returncode == 0:
                        q.put(("log", f"   - {part}: nothing to export (empty geometry)"))
                        skipped += 1
                    else:
                        q.put(("log", f"   x {part}: OpenSCAD failed (exit {result.returncode})"))
                        for tail_line in (result.stderr or "").strip().splitlines()[-5:]:
                            q.put(("log", f"       {tail_line}"))
                        failed += 1
                    done += 1
                    q.put(("progress", done))

            if dry_run:
                q.put(("log", "\nDry run finished — no files written."))
            else:
                q.put(("log", f"\nDone: {ok} exported, {skipped} skipped, {failed} failed -> {out_dir.resolve()}"))
        except SystemExit as e:
            q.put(("error", str(e)))
        except Exception as e:  # noqa: BLE001 - surface any failure to the UI instead of a silent thread death
            q.put(("error", f"Unexpected error: {e}"))
        finally:
            q.put(("done", None))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.log_queue.get_nowait()
                if kind == "log":
                    self._log(payload)
                elif kind == "max":
                    self.progress.configure(maximum=max(payload, 1))
                elif kind == "progress":
                    self.progress.configure(value=payload)
                elif kind == "error":
                    self._log(f"ERROR: {payload}")
                    messagebox.showerror("Error", payload)
                elif kind == "done":
                    self.run_btn.configure(state="normal")
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)


if __name__ == "__main__":
    TileApp().mainloop()
