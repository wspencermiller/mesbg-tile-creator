/* [Tile] */
tile_length    = 69;   // long side (X)
tile_width     = 26;   // short side (Y)
tile_thickness = 3;    // Z
corner_radius  = 2;
margin         = 2;    // keep-out border around all content

/* [Logo] */
// path to an SVG (same folder as this .scad, or absolute). Leave empty for no logo.
logo_file    = "logo.svg";
logo_percent = 20;     // logo width as % of tile length
logo_gap     = 2;      // space between logo and text block

/* [Text] */
font = "Liberation Sans:style=Bold";
// displayed on the tile (also used as the batch file-name stem)
name = "Gwaihir";
// profile values under MV FV SV S D A W C I (move uses inch marks, e.g. 8")
MV = "12\"";
FV = "8";
SV = "4+";
S  = "6";
D  = "8";
A  = "3";
W  = "3";
C  = "3+";
I  = "3+";
// MWF values (Will is named Will so it does not clash with Wounds = W)
M    = "3";
Will = "3";
F    = "3";
header_size = 3.5;
value_size  = 3.5;
name_size   = 7;        // starting size; shrinks if the wrapped lines don't fit
min_name_size = 2.5;    // name won't shrink below this
line_spacing = 1.25;    // name line pitch as a multiple of its size
row_gap     = 1.5;
name_gap    = 1.8;      // min clear space between the name and the profile / MWF rows
// average character width as a fraction of font size; raise it if text is still too wide
width_factor = 0.75;

/* [Style] */
// raised: sits on top | flush: inset, level with the surface | engraved: empty pocket
style      = "flush";   // [raised, flush, engraved]
text_depth = 0.6;

/* [Multi-color] */
part       = "all";     // [all, base only, text only, logo only]
base_color = "#f2f2f2"; // color
text_color = "#1f3a8a"; // color
logo_color = "#c2410c"; // color
clearance  = 0;         // pocket gap; ~0.1 only if printing pieces as loose inserts

/* [Hidden] */
profile_headers = ["MV", "FV", "SV", "S", "D", "A", "W", "C", "I"];
mwf_headers     = ["M", "W", "F"];
$fn = 48;

// ---------- string helpers ----------
function substr(s, st, n) = n <= 0 ? "" : str(s[st], substr(s, st + 1, n - 1));
function is_sep(c, seps) = len(search(c, seps)) > 0;
function _split(s, seps, i, start, acc) =
    i >= len(s) ? concat(acc, [substr(s, start, i - start)]) :
    is_sep(s[i], seps) ? _split(s, seps, i + 1, i + 1, concat(acc, [substr(s, start, i - start)])) :
                         _split(s, seps, i + 1, start, acc);
function split_str(s, seps = ",") = _split(s, seps, 0, 0, []);

// approximate rendered width
function est_w(s, size) = len(s) * size * width_factor;
// shrink a string so it fits within max_w
function fit(s, size, max_w) = est_w(s, size) > max_w ? size * max_w / est_w(s, size) : size;

// greedy word wrap
function wrap_words(words, size, max_w, i = 0, cur = "", acc = []) =
    i >= len(words) ? concat(acc, [cur]) :
    let (trial = cur == "" ? words[i] : str(cur, " ", words[i]))
    (cur != "" && est_w(trial, size) > max_w)
        ? wrap_words(words, size, max_w, i + 1, words[i], concat(acc, [cur]))
        : wrap_words(words, size, max_w, i + 1, trial, acc);

// name split at manual breaks (| or a real newline), then wrapped at spaces
function name_lines(size) =
    [for (p = split_str(name, str("|", chr(10))))
        each wrap_words([for (w = split_str(p, " ")) if (w != "") w], size, text_w)];

// ---------- layout ----------
has_logo = logo_file != "";
avail_w  = tile_length - 2 * margin;
avail_h  = tile_width  - 2 * margin;

logo_w   = tile_length * logo_percent / 100;
text_x0  = margin + (has_logo ? logo_w + logo_gap : 0);
text_w   = tile_length - margin - text_x0;

profile_values = [MV, FV, SV, S, D, A, W, C, I];
mwf_values     = [M, Will, F];
profile_ncols  = len(profile_headers);
mwf_ncols      = len(mwf_headers);
profile_col_w  = text_w / profile_ncols;
mwf_col_w      = text_w / mwf_ncols;

// profile + MWF share one scale; pin them to the top/bottom edges and
// give the leftover middle band to the name (with name_gap padding so
// wrapped names don't crowd the rows above/below)
block_raw = header_size + value_size + row_gap;
kh = min(1, 0.55 * avail_h / (2 * block_raw));
sh = header_size * kh;
sv = value_size * kh;
g  = row_gap * kh;
ng = name_gap * kh;
block_h = sh + sv + g;

// room left for the name after edge blocks + clear gaps above/below it
name_area_h = max(0, avail_h - 2 * block_h - 2 * ng);
// include a little glyph pad so baseline text doesn't eat into name_gap
function name_block_h(size) =
    let (n = len(name_lines(size)))
        size + (n - 1) * size * line_spacing + 0.25 * size;
function name_fits(size) = name_block_h(size) <= name_area_h;
function pick_name(size) =
    (name_fits(size) || size <= min_name_size) ? size : pick_name(size * 0.94);

sn       = pick_name(name_size);
n_lines  = name_lines(sn);
nn       = len(n_lines);
pitch    = sn * line_spacing;
name_h   = sn + (nn - 1) * pitch;

// profile flush to the top keep-out, MWF flush to the bottom keep-out
y_prof_h = margin + avail_h - sh / 2;
y_prof_v = y_prof_h - sh / 2 - g - sv / 2;
y_mwf_v  = margin + sv / 2;
y_mwf_h  = y_mwf_v + sv / 2 + g + sh / 2;
// name centered in the padded band between those two blocks
y_name0  = margin + block_h + ng + (name_area_h - name_block_h(sn)) / 2 + 0.125 * sn;

module txt(str_, size, x, y, va = "center") {
    if (len(str_) > 0)
        translate([x, y])
            text(str_, size = size, font = font, halign = "center", valign = va);
}

module labeled_row(headers, values, col_w, y_h, y_v) {
    ncols = len(headers);
    for (i = [0 : ncols - 1])
        txt(headers[i], fit(headers[i], sh, col_w - 0.4),
            text_x0 + col_w * (i + 0.5), y_h);
    for (i = [0 : min(len(values), ncols) - 1])
        txt(values[i], fit(values[i], sv, col_w - 0.4),
            text_x0 + col_w * (i + 0.5), y_v);
}

// ---------- 2D content ----------
module text_2d(grow = 0) {
    intersection() {
        offset(delta = grow) union() {
            labeled_row(profile_headers, profile_values, profile_col_w, y_prof_h, y_prof_v);
            // name: large, wrapped, centered in the text block
            intersection() {
                union()
                    for (j = [0 : nn - 1])
                        txt(n_lines[j], fit(n_lines[j], sn, text_w),
                            text_x0 + text_w / 2, y_name0 + (nn - 1 - j) * pitch, "baseline");
                translate([text_x0, margin]) square([text_w, avail_h]);
            }
            labeled_row(mwf_headers, mwf_values, mwf_col_w, y_mwf_h, y_mwf_v);
        }
        translate([margin, margin]) square([avail_w, avail_h]);
    }
}

module logo_2d(grow = 0) {
    if (has_logo)
        intersection() {
            offset(delta = grow)
                translate([margin + logo_w / 2, tile_width / 2])
                    resize([logo_w, 0], auto = true)
                        import(logo_file, center = true);
            translate([margin, margin]) square([logo_w, avail_h]);
        }
}

// ---------- 3D ----------
module rounded_tile() {
    r = min(corner_radius, tile_width / 2 - 0.01);
    linear_extrude(tile_thickness)
        offset(r = r) offset(delta = -r) square([tile_length, tile_width]);
}

module pocket(grow = 0) {
    translate([0, 0, tile_thickness - text_depth])
        linear_extrude(text_depth + 0.01) { text_2d(grow); logo_2d(grow); }
}

module base() {
    if (style == "raised") rounded_tile();
    else difference() { rounded_tile(); pocket(clearance); }
}

module piece(kind) {
    z = style == "raised" ? tile_thickness : tile_thickness - text_depth;
    if (style != "engraved")
        translate([0, 0, z])
            linear_extrude(text_depth)
                if (kind == "text") text_2d(); else logo_2d();
}

if (part == "all" || part == "base only") color(base_color) base();
if (part == "all" || part == "text only") color(text_color) piece("text");
if (part == "all" || part == "logo only") color(logo_color) piece("logo");
