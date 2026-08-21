"""
build_deforestation_map.py

Builds a self-contained Leaflet map of tree cover loss (deforestation) across
Romania's 42 counties, 2001-2025, using real data pulled from the public
Global Nature Watch (formerly Global Forest Watch) data API — the same
Hansen/UMD/Google/USGS/NASA dataset that powers globalforestwatch.org.

Data sources baked in (fetched 2026-08-20):
  - County boundaries: GADM v3.6 admin-1 (via GabrielRondelli/geojson on GitHub),
    simplified with mapshaper.
  - Tree cover loss by county/year: gadm__tcl__adm1_change dataset,
    canopy density threshold 30%, globalnaturewatch.org/api/data/dataset/...
  - National totals by year + loss driver breakdown: gadm__tcl__iso_change dataset.

Usage:
  python build_deforestation_map.py --out romania_deforestation_map.html
"""

import argparse
import csv
import json
import sys

# ---------------------------------------------------------------------------
# Hardcoded stats pulled live from globalnaturewatch.org's public data API
# (see claude/deforestation-map-feasibility.md and the fetch log for how).
# ---------------------------------------------------------------------------

NATIONAL_BY_YEAR = {
    2001: 17535, 2002: 16356, 2003: 9428, 2004: 18859, 2005: 19418,
    2006: 13067, 2007: 38082, 2008: 17536, 2009: 16177, 2010: 17782,
    2011: 16928, 2012: 30649, 2013: 12946, 2014: 19482, 2015: 10906,
    2016: 23045, 2017: 19187, 2018: 18974, 2019: 12266, 2020: 27445,
    2021: 14700, 2022: 16516, 2023: 25380, 2024: 20153, 2025: 23475,
}

DRIVERS = [
    ("Logging", 458682),
    ("Unknown", 5253),
    ("Other natural disturbances", 3448),
    ("Permanent agriculture", 3317),
    ("Hard commodities", 2185),
    ("Settlements & Infrastructure", 2143),
    ("Wildfire", 1266),
]

# Sequential forest-green ramp (same L/C step schedule as the dataviz skill's
# reference blue ramp, rotated to hue 142.5° OKLCH — a forest/pine green,
# matching the skill's own categorical "green" slot — then gamut-mapped to
# sRGB; lightness is strictly monotone light->dark by construction).
SEQ_RAMP = ["#d1e7ce", "#a4cfa0", "#77b671", "#429e3d", "#297f25", "#196116", "#0c440a"]
# Fixed categorical order (dataviz skill reference palette)
CAT_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7"]


def load_counties(geojson_path, csv_path):
    with open(geojson_path, encoding="utf-8") as f:
        gj = json.load(f)

    loss_by_adm1 = {}
    years = None
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        years = [int(y) for y in header[2:]]
        for row in reader:
            adm1 = int(row[0])
            name = row[1]
            vals = [int(v) for v in row[2:]]
            loss_by_adm1[adm1] = {"name": name, "years": dict(zip(years, vals))}

    for feat in gj["features"]:
        adm1 = feat["properties"]["ID_1"]
        entry = loss_by_adm1.get(adm1)
        feat["properties"] = {
            "adm1": adm1,
            "name": entry["name"] if entry else feat["properties"].get("NAME_1"),
            "years": entry["years"] if entry else {},
        }

    return gj, years


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--geojson", default="romania-counties-simplified.geojson")
    ap.add_argument("--csv", default="gfw_romania_county_loss.csv")
    ap.add_argument("--out", default="romania_deforestation_map.html")
    args = ap.parse_args()

    print("Loading county boundaries + loss data...", file=sys.stderr)
    gj, years = load_counties(args.geojson, args.csv)
    print(f"  -> {len(gj['features'])} counties, years {years[0]}-{years[-1]}", file=sys.stderr)

    total_national = sum(NATIONAL_BY_YEAR.values())
    recent5 = sum(v for y, v in NATIONAL_BY_YEAR.items() if y >= 2021)
    logging_share = DRIVERS[0][1] / sum(d[1] for d in DRIVERS) * 100

    print(f"  -> total national loss 2001-2025: {total_national:,} ha", file=sys.stderr)
    print(f"  -> logging share of all loss: {logging_share:.1f}%", file=sys.stderr)

    html = HTML_TEMPLATE
    html = html.replace("__COUNTIES__", json.dumps(gj, ensure_ascii=False))
    html = html.replace("__YEARS__", json.dumps(years))
    html = html.replace("__NATIONAL__", json.dumps(NATIONAL_BY_YEAR))
    html = html.replace("__DRIVERS__", json.dumps(DRIVERS, ensure_ascii=False))
    html = html.replace("__SEQ_RAMP__", json.dumps(SEQ_RAMP))
    html = html.replace("__CAT_COLORS__", json.dumps(CAT_COLORS))
    html = html.replace("__TOTAL_NATIONAL__", str(total_national))
    html = html.replace("__RECENT5__", str(recent5))
    html = html.replace("__LOGGING_SHARE__", f"{logging_share:.0f}")
    html = html.replace("__YEARS_RANGE_2016_2025__", json.dumps(list(range(2016, 2026))))

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n  -> written to {args.out}", file=sys.stderr)


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>Romania Deforestation Map — Tree Cover Loss 2001-2025</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<style>
:root {
  color-scheme: light;
  --surface-1:      #fcfcfb;
  --page-plane:     #f9f9f7;
  --text-primary:   #0b0b0b;
  --text-secondary: #52514e;
  --text-muted:     #898781;
  --gridline:       #e1e0d9;
  --baseline:       #c3c2b7;
  --border:         rgba(11,11,11,0.10);
  --seq-100: #d1e7ce; --seq-200: #a4cfa0; --seq-300: #77b671; --seq-400: #429e3d;
  --seq-500: #297f25; --seq-600: #196116; --seq-700: #0c440a;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  background: var(--page-plane); color: var(--text-primary);
  display: flex; height: 100dvh; overflow: hidden;
}
#map-container { flex: 1; position: relative; min-width: 0; }
#map { height: 100%; }
/* map2: the "after" photo in Compare-imagery mode, a second Leaflet map stacked
   exactly over #map in a plain (untransformed) wrapper div, so clip-path on THIS
   div — not on a Leaflet-internal pane — correctly reveals it right of the divider. */
#map2 {
  position: absolute; inset: 0; z-index: 500;
  pointer-events: none; display: none;
  clip-path: inset(0 0 0 50%);
}
#map2.visible { display: block; }

#top-overlay { display: contents; }
#bottom-overlay { display: contents; }

#header {
  position: absolute; top: 12px; left: 12px; z-index: 1000;
  background: var(--surface-1); border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.12);
  padding: 16px 18px; width: 310px; max-height: calc(100% - 24px);
  overflow-y: auto; border: 1px solid var(--border);
}
#header h1 { font-size: 18px; font-weight: 700; }
#header .sub { font-size: 14px; color: var(--text-secondary); margin-top: 4px; line-height: 1.4; }
.hstat { display: flex; align-items: baseline; gap: 7px; margin-top: 11px; }
.hstat .v { font-size: 27px; font-weight: 800; color: var(--seq-600); line-height: 1; }
.hstat .l { font-size: 13px; color: var(--text-secondary); line-height: 1.3; }

#year-panel {
  position: absolute; bottom: 12px; left: 12px; right: 12px; z-index: 1000;
  background: var(--surface-1); border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.12);
  padding: 12px 16px; border: 1px solid var(--border);
}
#year-panel .row { display: flex; align-items: center; gap: 10px; }
#year-panel label { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); white-space: nowrap; }
#year-label { font-size: 15px; font-weight: 700; color: var(--seq-600); white-space: nowrap; min-width: 128px; text-align: right; }
#year-chart { height: 44px; margin-top: 8px; }

/* Dual-handle range slider: two native inputs overlaid on one shared track,
   so it reads as ONE "from year -> to year" control, not two separate sliders. */
.range-wrap { position: relative; flex: 1; height: 24px; }
.range-track-bg, .range-track-fill {
  position: absolute; top: 50%; transform: translateY(-50%);
  height: 4px; border-radius: 2px; pointer-events: none;
}
.range-track-bg { left: 0; right: 0; background: var(--gridline); }
.range-track-fill { background: var(--seq-500); }
.range-wrap input[type=range] {
  position: absolute; left: 0; right: 0; top: 0; width: 100%; height: 24px;
  margin: 0; background: transparent; -webkit-appearance: none; appearance: none;
  pointer-events: none; /* only the thumb (re-enabled below) is clickable */
}
.range-wrap input[type=range]::-webkit-slider-runnable-track { background: transparent; height: 4px; }
.range-wrap input[type=range]::-moz-range-track { background: transparent; height: 4px; border: none; }
.range-wrap input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none; pointer-events: auto; cursor: pointer;
  width: 22px; height: 22px; border-radius: 50%; margin-top: -9px;
  background: var(--seq-600); border: 2px solid var(--surface-1);
  box-shadow: 0 1px 3px rgba(0,0,0,0.35);
}
.range-wrap input[type=range]::-moz-range-thumb {
  pointer-events: auto; cursor: pointer; width: 22px; height: 22px; border-radius: 50%;
  background: var(--seq-600); border: 2px solid var(--surface-1); box-shadow: 0 1px 3px rgba(0,0,0,0.35);
}
.range-ends { display: flex; justify-content: space-between; margin-top: 2px; }
.range-ends span { font-size: 12px; color: var(--text-muted); }

#basemap-toggle {
  position: absolute; top: 12px; right: 12px; z-index: 1000;
  background: var(--surface-1); border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.15); border: 1px solid var(--border);
  display: flex; overflow: hidden; font-size: 13px; font-weight: 600;
}
#basemap-toggle button {
  border: none; background: transparent; padding: 11px 14px; cursor: pointer;
  color: var(--text-secondary);
}
#basemap-toggle button.active { background: var(--seq-500); color: white; }

#legend {
  position: absolute; top: 64px; right: 12px; z-index: 1000;
  background: var(--surface-1); border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.15); border: 1px solid var(--border);
  padding: 11px 13px; font-size: 13px; color: var(--text-secondary);
}
#legend .title { font-weight: 700; color: var(--text-primary); margin-bottom: 7px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; }
#legend .ramp { display: flex; height: 12px; border-radius: 3px; overflow: hidden; width: 210px; }
#legend .ramp div { flex: 1; }
#legend .scale-labels { display: flex; justify-content: space-between; margin-top: 4px; }

#compare-panel {
  position: absolute; top: 64px; right: 12px; z-index: 1000;
  background: var(--surface-1); border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.15); border: 1px solid var(--border);
  padding: 11px 13px; font-size: 13px; color: var(--text-secondary);
  display: none; width: 250px;
}
#compare-panel.visible { display: block; }
#compare-panel .title { font-weight: 700; color: var(--text-primary); margin-bottom: 9px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; }
.cmp-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 7px; }
.cmp-row label { font-size: 13px; color: var(--text-secondary); flex-shrink: 0; }
.cmp-row select {
  font-size: 13px; font-weight: 700; color: var(--text-primary); background: var(--page-plane);
  border: 1px solid var(--border); border-radius: 6px; padding: 4px 7px; cursor: pointer;
}
.cmp-swatch { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 5px; }
#compare-panel .cmp-note { font-size: 12px; color: var(--text-muted); line-height: 1.4; margin-top: 7px; padding-top: 7px; border-top: 1px solid var(--gridline); }

.swipe-divider {
  position: absolute; top: 0; bottom: 0; width: 0; z-index: 999;
  border-left: 2px solid #ffffff; box-shadow: 0 0 0 1px rgba(0,0,0,0.25);
  cursor: ew-resize; display: none;
}
.swipe-divider.visible { display: block; }
.swipe-handle {
  position: absolute; top: 50%; left: 0; transform: translate(-50%, -50%);
  width: 40px; height: 40px; border-radius: 50%; background: #ffffff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center;
  font-size: 16px; color: var(--seq-600); user-select: none;
}
.swipe-label {
  position: absolute; top: 12px; z-index: 999; background: rgba(11,11,11,0.65); color: #fff;
  font-size: 13px; font-weight: 700; padding: 5px 11px; border-radius: 6px; display: none; pointer-events: none;
}
.swipe-label.visible { display: block; }
#swipe-label-before { left: 12px; }
#swipe-label-after { right: 12px; }

#sidebar {
  width: 340px; flex-shrink: 0; background: var(--surface-1);
  border-left: 1px solid var(--gridline); overflow-y: auto;
  padding: 20px 18px; display: flex; flex-direction: column; gap: 20px;
}
.sec-label { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin-bottom: 9px; }
.sec-sub { font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 11px; }

.rank-row { display: flex; align-items: center; gap: 8px; padding: 4px 0; cursor: pointer; }
.rank-row:hover .rank-name { color: var(--seq-600); }
.rank-name { font-size: 13px; color: var(--text-primary); width: 100px; flex-shrink: 0; }
.rank-bar-wrap { flex: 1; height: 13px; background: var(--gridline); border-radius: 3px; overflow: hidden; }
.rank-bar { height: 100%; background: var(--seq-500); border-radius: 3px; }
.rank-val { font-size: 12px; color: var(--text-secondary); width: 62px; text-align: right; flex-shrink: 0; }

.driver-row { display: flex; align-items: center; gap: 10px; padding: 5px 0; }
.driver-chip { width: 11px; height: 11px; border-radius: 3px; flex-shrink: 0; }
.driver-name { font-size: 13px; color: var(--text-primary); flex: 1; }
.driver-val { font-size: 14px; font-weight: 700; color: var(--text-primary); width: 52px; text-align: right; flex-shrink: 0; }

.trend-svg { width: 100%; height: 90px; }
.trend-svg path.line { fill: none; stroke: var(--seq-500); stroke-width: 2; }
.trend-svg path.area { fill: var(--seq-100); opacity: 0.6; }
.trend-svg line.grid { stroke: var(--gridline); stroke-width: 1; }
.trend-svg text.tick { fill: var(--text-muted); font-size: 11px; }

.explore-link {
  display: block; font-size: 13px; color: var(--seq-600); text-decoration: none;
  padding: 7px 0; border-top: 1px solid var(--gridline);
}
.explore-link:hover { text-decoration: underline; }

.source-note { font-size: 11px; color: var(--text-muted); line-height: 1.5; padding-top: 11px; border-top: 1px solid var(--gridline); }
.source-note a { color: var(--text-muted); }

.leaflet-popup-content { min-width: 200px; font-size: 14px; line-height: 1.6; }
.leaflet-popup-content b { display: block; font-size: 15px; margin-bottom: 4px; }
.popup-total { color: #196116; font-weight: 700; }

.leaflet-control-attribution { font-size: 11px; }

@media (max-width: 900px) {
  body { flex-direction: column; }
  #sidebar { width: 100%; max-height: 34dvh; order: 2; }
  #map-container { order: 1; min-height: 60dvh; }

  /* Header + mode toggle stack vertically as full-width rows instead of
     sitting side by side (on a phone-width screen they collided: the
     toggle's three buttons overlapped the header's title/stats). The
     header itself is condensed — the long description drops and the two
     headline stats sit side by side instead of stacked — so the whole
     top group stays short enough to leave real room for the map. */
  #top-overlay {
    display: flex; flex-direction: column; gap: 8px;
    position: absolute; top: 10px; left: 10px; right: 10px; z-index: 1000;
  }
  #header {
    position: static; width: 100%; max-height: none;
    padding: 10px 14px; display: flex; flex-wrap: wrap; align-items: baseline; gap: 2px 18px;
  }
  #header h1 { flex: 1 0 100%; font-size: 16px; }
  #header .sub { display: none; }
  .hstat { margin-top: 4px; }
  .hstat .v { font-size: 21px; }
  .hstat .l { font-size: 11px; }
  #basemap-toggle { position: static; width: 100%; font-size: 12.5px; }
  #basemap-toggle button { flex: 1; padding: 10px 6px; text-align: center; }

  /* Legend / compare-panel / year-panel stack as one bottom-anchored
     column instead of independent floating cards — on a short viewport,
     fixed pixel offsets (the old approach) put compare-panel's taller
     content up underneath the header/toggle stack instead of leaving it
     hidden below the fold; flowing them in order keeps every card fully
     visible and non-overlapping regardless of exactly how tall each one
     renders. */
  #bottom-overlay {
    display: flex; flex-direction: column; gap: 8px;
    position: absolute; bottom: 10px; left: 10px; right: 10px; z-index: 1000;
  }
  #legend, #compare-panel, #year-panel { position: static; width: 100%; }
  #compare-panel .cmp-note { display: none; }
  #year-chart { height: 34px; }

  /* Leaflet's own bottom-right credit line can wrap to 2 lines on a narrow
     screen (the EOX compare-imagery credit is long) and poke out past the
     year-panel that's meant to sit over it — keep it to one short line. */
  .leaflet-control-attribution {
    max-width: 60vw; font-size: 9px; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
  }

  .swipe-handle { width: 44px; height: 44px; font-size: 18px; }
}
</style>
</head>
<body>

<div id="map-container">
  <div id="map"></div>
  <div id="map2"></div>

  <div id="top-overlay">
    <div id="header">
      <h1>🌲 Romania Deforestation Map</h1>
      <div class="sub">Tree cover loss by county, 2001–2024 · Hansen/UMD/Google/USGS/NASA data via Global Nature Watch</div>
      <div class="hstat"><span class="v" id="hs-total"></span><span class="l">hectares of tree cover lost<br>nationwide, 2001–2025</span></div>
      <div class="hstat"><span class="v" id="hs-logging"></span><span class="l">of all tracked loss is<br>attributed to logging</span></div>
    </div>

    <div id="basemap-toggle">
      <button id="btn-osm" class="active">Map</button>
      <button id="btn-sat">Satellite</button>
      <button id="btn-cmp">Compare imagery</button>
    </div>
  </div>

  <div class="swipe-divider" id="swipe-divider"><div class="swipe-handle">⇔</div></div>
  <div class="swipe-label" id="swipe-label-before">BEFORE</div>
  <div class="swipe-label" id="swipe-label-after">AFTER</div>

  <div id="bottom-overlay">
    <div id="legend">
      <div class="title">Tree cover lost (ha, selected years)</div>
      <div class="ramp" id="legend-ramp"></div>
      <div class="scale-labels"><span>0</span><span id="legend-max">high</span></div>
    </div>

    <div id="compare-panel">
      <div class="title">Real satellite imagery</div>
      <div class="cmp-row">
        <label><span class="cmp-swatch" style="background:#898781"></span>Before</label>
        <select id="cmp-before"></select>
      </div>
      <div class="cmp-row">
        <label><span class="cmp-swatch" style="background:#196116"></span>After</label>
        <select id="cmp-after"></select>
      </div>
      <div class="cmp-note">Drag the white divider on the map to reveal before/after. Sentinel-2 cloudless annual mosaics, EOX IT Services — real photos, not modeled data. Pan/zoom to any county (try Suceava or Harghita, the top two by loss).</div>
    </div>

    <div id="year-panel">
      <div class="row">
        <label>Years</label>
        <div class="range-wrap">
          <div class="range-track-bg"></div>
          <div class="range-track-fill" id="range-fill"></div>
          <input type="range" id="year-min" min="2001" max="2025" value="2001" step="1">
          <input type="range" id="year-max" min="2001" max="2025" value="2025" step="1">
        </div>
        <span id="year-label">2001 – 2024</span>
      </div>
      <div class="range-ends"><span id="range-end-lo"></span><span id="range-end-hi"></span></div>
      <svg class="trend-svg" id="year-chart"></svg>
    </div>
  </div>
</div>

<div id="sidebar">
  <div>
    <div class="sec-label">Highest cumulative loss</div>
    <div class="sec-sub">Counties ranked by tree cover lost in the selected year range. Click a bar or a county on the map for its yearly detail.</div>
    <div id="ranking"></div>
  </div>

  <div>
    <div class="sec-label">Why the forest is disappearing</div>
    <div class="sec-sub">Cause of tree cover loss nationwide, 2001–2024, by dominant driver (Hansen/WRI classification).</div>
    <div id="drivers"></div>
  </div>

  <div>
    <div class="sec-label">National trend</div>
    <div class="sec-sub">Total hectares of tree cover lost per year, all counties. Includes 2025 nationally; the county map and ranking above cover 2001–2024 (latest year with a per-county breakdown available).</div>
    <svg class="trend-svg" id="national-trend"></svg>
  </div>

  <div>
    <div class="sec-label">See the actual satellite imagery</div>
    <div class="sec-sub">The county colors above are <i>data</i> — where and how much forest disappeared, not a photo. For real before/after photos in this same map, click <b>"Compare imagery"</b> at the top right and drag the divider. Or explore externally:</div>
    <a class="explore-link" id="link-eobrowser" href="#" target="_blank" rel="noopener">↗ Open Romania in Copernicus Browser (Sentinel-2, pick any two dates)</a>
    <a class="explore-link" id="link-gfw" href="#" target="_blank" rel="noopener">↗ Open Romania on Global Forest Watch</a>
  </div>

  <div class="source-note">
    Tree cover loss: Hansen/UMD/Google/USGS/NASA Global Forest Change, ≥30% canopy density threshold, via the public
    <a href="https://globalnaturewatch.org" target="_blank">Global Nature Watch</a> data API (formerly Global Forest Watch), CC BY 4.0.
    Loss driver classification: WRI/Google. County boundaries: GADM v3.6.
    Compare-imagery photos: Sentinel-2 cloudless annual mosaics by <a href="https://s2maps.eu" target="_blank">EOX IT Services GmbH</a>, contains modified Copernicus Sentinel data, CC BY-SA 4.0.
    Data fetched 2026-08-20 — GNW updates annually; figures may since have shifted slightly.
  </div>
</div>

<script>
const COUNTIES = __COUNTIES__;
const YEARS = __YEARS__;
const NATIONAL = __NATIONAL__;
const DRIVERS = __DRIVERS__;
const SEQ_RAMP = __SEQ_RAMP__;
const CAT_COLORS = __CAT_COLORS__;

document.getElementById('hs-total').textContent = (__TOTAL_NATIONAL__).toLocaleString('en-US');
document.getElementById('hs-logging').textContent = '__LOGGING_SHARE__%';

// ---- MAP SETUP ----
const map = L.map('map', { preferCanvas: true }).setView([45.94, 24.97], 7);
const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 18,
}).addTo(map);
const sat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Esri, Maxar, Earthstar Geographics',
  maxZoom: 18,
});

// ---- COMPARE-IMAGERY MODE ----
// Real Sentinel-2 photography (not modeled/colored data) via EOX's public annual
// "Sentinel-2 cloudless" mosaics — one real image per year, 2016 onward.
//
// Implementation note: a naive version of this clips a Leaflet *pane* with
// CSS clip-path — but panes are large, panned via `transform`, and don't line
// up with the visible viewport, so a percentage clip-path on a pane clips the
// wrong region (usually making the layer vanish entirely). The robust fix is
// two independent Leaflet maps stacked in plain, untransformed wrapper divs:
// `map` (the real one, draggable/zoomable — shows the "before" photo) and
// `map2` (a second map in an overlay div, non-interactive, kept in perfect
// sync with `map`'s center/zoom — shows the "after" photo). Because map2's
// *wrapper div* is an ordinary block element sized to the viewport, clipping
// that div's own box with clip-path works correctly, revealing "after" only
// to the right of the divider while "before" (and the county outlines) show
// through underneath everywhere else.
const EOX_ATTR = 'Sentinel-2 cloudless by <a href="https://s2maps.eu" target="_blank">EOX IT Services GmbH</a> (Contains modified Copernicus Sentinel data), CC BY-SA 4.0';
const CMP_YEARS = __YEARS_RANGE_2016_2025__;
function eoxUrl(year) {
  return `https://e.tiles.maps.eox.at/wmts/1.0.0/s2cloudless-${year}_3857/default/GoogleMapsCompatible/{z}/{y}/{x}.jpg`;
}
let cmpBeforeYear = '2018', cmpAfterYear = String(CMP_YEARS[CMP_YEARS.length - 1] - 1);
const cmpBefore = L.tileLayer(eoxUrl(cmpBeforeYear), { maxZoom: 13, attribution: EOX_ATTR });

const map2El = document.getElementById('map2');
const map2 = L.map(map2El, {
  attributionControl: false, zoomControl: false, dragging: false, scrollWheelZoom: false,
  doubleClickZoom: false, boxZoom: false, keyboard: false, tap: false, touchZoom: false, fadeAnimation: false,
});
const cmpAfter = L.tileLayer(eoxUrl(cmpAfterYear), { maxZoom: 13, attribution: EOX_ATTR }).addTo(map2);
function syncMap2() { map2.setView(map.getCenter(), map.getZoom(), { animate: false }); }
map.on('move zoom', syncMap2);

const beforeSelect = document.getElementById('cmp-before');
const afterSelect = document.getElementById('cmp-after');
CMP_YEARS.forEach(y => {
  beforeSelect.add(new Option(y, y, false, String(y) === cmpBeforeYear));
  afterSelect.add(new Option(y, y, false, String(y) === cmpAfterYear));
});
beforeSelect.onchange = () => { cmpBeforeYear = beforeSelect.value; cmpBefore.setUrl(eoxUrl(cmpBeforeYear)); };
afterSelect.onchange = () => { cmpAfterYear = afterSelect.value; cmpAfter.setUrl(eoxUrl(cmpAfterYear)); };

const divider = document.getElementById('swipe-divider');
const labelBefore = document.getElementById('swipe-label-before');
const labelAfter = document.getElementById('swipe-label-after');
let dividerPct = 50;
function applyDivider() {
  const w = document.getElementById('map').clientWidth;
  divider.style.left = (w * dividerPct / 100) + 'px';
  map2El.style.clipPath = `inset(0 0 0 ${dividerPct}%)`;
}
function startDrag(clientX) {
  const rect = document.getElementById('map').getBoundingClientRect();
  const onMove = e => {
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
    dividerPct = Math.min(100, Math.max(0, x / rect.width * 100));
    applyDivider();
  };
  const onUp = () => {
    window.removeEventListener('mousemove', onMove);
    window.removeEventListener('mouseup', onUp);
    window.removeEventListener('touchmove', onMove);
    window.removeEventListener('touchend', onUp);
  };
  window.addEventListener('mousemove', onMove);
  window.addEventListener('mouseup', onUp);
  window.addEventListener('touchmove', onMove);
  window.addEventListener('touchend', onUp);
}
divider.addEventListener('mousedown', e => { e.preventDefault(); startDrag(e.clientX); });
divider.addEventListener('touchstart', e => startDrag(e.touches[0].clientX), { passive: true });
window.addEventListener('resize', () => { if (mode === 'compare') { map2.invalidateSize(); applyDivider(); } });
map.on('resize', () => { if (mode === 'compare') { map2.invalidateSize(); applyDivider(); } });

let mode = 'map';
function setMode(next) {
  mode = next;
  [osm, sat, cmpBefore].forEach(l => map.removeLayer(l));
  map2El.classList.toggle('visible', mode === 'compare');
  document.getElementById('compare-panel').classList.toggle('visible', mode === 'compare');
  divider.classList.toggle('visible', mode === 'compare');
  labelBefore.classList.toggle('visible', mode === 'compare');
  labelAfter.classList.toggle('visible', mode === 'compare');
  document.getElementById('legend').style.display = mode === 'compare' ? 'none' : 'block';

  if (mode === 'map') map.addLayer(osm);
  else if (mode === 'satellite') map.addLayer(sat);
  else if (mode === 'compare') {
    map.addLayer(cmpBefore);
    syncMap2();
    map2.invalidateSize();
    applyDivider();
  }

  document.getElementById('btn-osm').classList.toggle('active', mode === 'map');
  document.getElementById('btn-sat').classList.toggle('active', mode === 'satellite');
  document.getElementById('btn-cmp').classList.toggle('active', mode === 'compare');

  if (geoLayer) render();
}
document.getElementById('btn-osm').onclick = () => setMode('map');
document.getElementById('btn-sat').onclick = () => setMode('satellite');
document.getElementById('btn-cmp').onclick = () => setMode('compare');

// ---- COLOR SCALE ----
function colorFor(value, maxValue) {
  if (!value || value <= 0) return SEQ_RAMP[0];
  const t = Math.log(value + 1) / Math.log(maxValue + 1);
  const idx = Math.min(SEQ_RAMP.length - 1, Math.floor(t * SEQ_RAMP.length));
  return SEQ_RAMP[idx];
}

function sumRange(yearsObj, y0, y1) {
  let s = 0;
  for (let y = y0; y <= y1; y++) s += (yearsObj[y] || 0);
  return s;
}

let geoLayer = null;
let geoLayer2 = null;
let selectedAdm1 = null;
const COUNTY_YEAR_MIN = Math.min(...YEARS);
const COUNTY_YEAR_MAX = Math.max(...YEARS);
const state = { y0: COUNTY_YEAR_MIN, y1: COUNTY_YEAR_MAX };

function render() {
  const values = COUNTIES.features.map(f => sumRange(f.properties.years, state.y0, state.y1));
  const maxValue = Math.max(...values, 1);

  document.getElementById('legend-max').textContent = Math.round(maxValue).toLocaleString('en-US') + ' ha';
  document.getElementById('legend-ramp').innerHTML = SEQ_RAMP.map(c => `<div style="background:${c}"></div>`).join('');

  const countyStyle = f => {
    const v = sumRange(f.properties.years, state.y0, state.y1);
    const isSel = f.properties.adm1 === selectedAdm1;
    if (mode === 'compare') {
      // Real imagery mode: near-invisible fill (it would hide the photo if opaque,
      // but a fully-zero fill stops clicks registering except right on the line) —
      // just a thin reference outline so county borders stay visible over the photo.
      return { fillOpacity: 0.01, fillColor: '#ffffff', color: isSel ? '#ffe14d' : 'rgba(255,255,255,0.55)', weight: isSel ? 2.5 : 1 };
    }
    return {
      fillColor: colorFor(v, maxValue),
      fillOpacity: 0.82,
      color: isSel ? '#0b0b0b' : '#ffffff',
      weight: isSel ? 2.5 : 1,
    };
  };

  if (geoLayer) map.removeLayer(geoLayer);
  geoLayer = L.geoJSON(COUNTIES, {
    style: countyStyle,
    onEachFeature: (f, layer) => {
      layer.on('click', () => { selectedAdm1 = f.properties.adm1; render(); showPopup(f, layer); });
      layer.on('mouseover', () => layer.setStyle({ weight: 2.5 }));
      layer.on('mouseout', () => { if (f.properties.adm1 !== selectedAdm1) layer.setStyle({ weight: 1 }); });
    }
  }).addTo(map);

  // Mirror outline-only layer on map2 (the "after" compare-imagery instance), so county
  // borders stay visible on the right side of the swipe divider too, not just the left
  // side (which sits on the primary `map` and its `geoLayer` above). Non-interactive:
  // map2's container has pointer-events:none, so no click handlers are needed here.
  if (geoLayer2) map2.removeLayer(geoLayer2);
  geoLayer2 = L.geoJSON(COUNTIES, { style: countyStyle }).addTo(map2);

  renderRanking(values);
  renderYearChart();
}

function showPopup(f, layer) {
  const v = sumRange(f.properties.years, state.y0, state.y1);
  const rank = rankOf(f.properties.adm1);
  layer.bindPopup(
    `<b>${f.properties.name}</b>` +
    `<span class="popup-total">${Math.round(v).toLocaleString('en-US')} ha</span> lost, ${state.y0}–${state.y1}<br>` +
    `Rank ${rank} of 42 counties<br>` +
    `<a href="#" onclick="window.open('https://browser.dataspace.copernicus.eu/?zoom=10&lat=' + ${layer.getBounds().getCenter().lat} + '&lng=' + ${layer.getBounds().getCenter().lng}, '_blank'); return false;">↗ view real satellite imagery here</a>`
  ).openPopup();
}

function rankOf(adm1) {
  const totals = COUNTIES.features.map(f => ({ adm1: f.properties.adm1, v: sumRange(f.properties.years, state.y0, state.y1) }));
  totals.sort((a, b) => b.v - a.v);
  return totals.findIndex(t => t.adm1 === adm1) + 1;
}

function renderRanking(values) {
  const rows = COUNTIES.features.map((f, i) => ({ name: f.properties.name, adm1: f.properties.adm1, v: values[i] }));
  rows.sort((a, b) => b.v - a.v);
  const top = rows.slice(0, 10);
  const maxV = top[0] ? top[0].v : 1;
  document.getElementById('ranking').innerHTML = top.map(r => `
    <div class="rank-row" data-adm1="${r.adm1}">
      <span class="rank-name">${r.name}</span>
      <div class="rank-bar-wrap"><div class="rank-bar" style="width:${(r.v/maxV*100).toFixed(1)}%"></div></div>
      <span class="rank-val">${Math.round(r.v).toLocaleString('en-US')}</span>
    </div>
  `).join('');
  document.querySelectorAll('.rank-row').forEach(el => {
    el.onclick = () => {
      const adm1 = parseInt(el.dataset.adm1);
      selectedAdm1 = adm1;
      const feat = COUNTIES.features.find(f => f.properties.adm1 === adm1);
      const layer = Object.values(geoLayer._layers).find(l => l.feature.properties.adm1 === adm1);
      render();
      if (layer) {
        map.fitBounds(layer.getBounds(), { maxZoom: 9 });
        showPopup(feat, layer);
      }
    };
  });
}

function renderDrivers() {
  // Percentage of total, not a magnitude bar: logging so dominates the other
  // six causes (96%+ of all tracked loss) that a bar scaled to the largest
  // category made every other row's bar disappear to a sliver. A share-of-
  // total number reads correctly at any skew.
  const total = DRIVERS.reduce((s, d) => s + d[1], 0);
  document.getElementById('drivers').innerHTML = DRIVERS.map((d, i) => `
    <div class="driver-row">
      <span class="driver-chip" style="background:${CAT_COLORS[i % CAT_COLORS.length]}"></span>
      <span class="driver-name">${d[0]}</span>
      <span class="driver-val">${(d[1] / total * 100).toFixed(1)}%</span>
    </div>
  `).join('');
}

function svgLineChart(el, dataObj, y0, y1, highlightRange) {
  const w = el.clientWidth || 280, h = 90, pad = { l: 4, r: 4, t: 8, b: 16 };
  const yearsArr = Object.keys(dataObj).map(Number).sort((a,b)=>a-b);
  const vals = yearsArr.map(y => dataObj[y]);
  const maxV = Math.max(...vals, 1);
  const x = y => pad.l + (y - yearsArr[0]) / (yearsArr[yearsArr.length-1] - yearsArr[0]) * (w - pad.l - pad.r);
  const yFn = v => h - pad.b - (v / maxV) * (h - pad.t - pad.b);
  let d = 'M ' + yearsArr.map(y => `${x(y)},${yFn(dataObj[y])}`).join(' L ');
  let area = d + ` L ${x(yearsArr[yearsArr.length-1])},${h-pad.b} L ${x(yearsArr[0])},${h-pad.b} Z`;
  let highlight = '';
  if (highlightRange) {
    const [hy0, hy1] = highlightRange;
    highlight = `<rect x="${x(Math.max(hy0,yearsArr[0]))}" y="${pad.t}" width="${x(Math.min(hy1,yearsArr[yearsArr.length-1]))-x(Math.max(hy0,yearsArr[0]))}" height="${h-pad.t-pad.b}" fill="var(--seq-100)" opacity="0.5"/>`;
  }
  el.setAttribute('viewBox', `0 0 ${w} ${h}`);
  el.innerHTML = `
    ${highlight}
    <line class="grid" x1="${pad.l}" y1="${h-pad.b}" x2="${w-pad.r}" y2="${h-pad.b}"/>
    <path class="area" d="${area}"/>
    <path class="line" d="${d}"/>
    <text class="tick" x="${pad.l}" y="${h-4}">${yearsArr[0]}</text>
    <text class="tick" x="${w-pad.r-24}" y="${h-4}">${yearsArr[yearsArr.length-1]}</text>
  `;
}

function renderYearChart() {
  svgLineChart(document.getElementById('year-chart'), NATIONAL, 2001, 2025, [state.y0, state.y1]);
  svgLineChart(document.getElementById('national-trend'), NATIONAL, 2001, 2025, [state.y0, state.y1]);
}

// ---- YEAR SLIDER (dual-handle: two inputs sharing one visual track) ----
const minSlider = document.getElementById('year-min');
const maxSlider = document.getElementById('year-max');
const yearLabel = document.getElementById('year-label');
const rangeFill = document.getElementById('range-fill');
document.getElementById('range-end-lo').textContent = COUNTY_YEAR_MIN;
document.getElementById('range-end-hi').textContent = COUNTY_YEAR_MAX;
minSlider.min = maxSlider.min = COUNTY_YEAR_MIN;
minSlider.max = maxSlider.max = COUNTY_YEAR_MAX;
minSlider.value = COUNTY_YEAR_MIN;
maxSlider.value = COUNTY_YEAR_MAX;

function updateYears() {
  // Clamp instead of letting the handles cross — the "from" handle can never
  // pass the "to" handle, so they can't swap roles and confuse which is which.
  let y0 = parseInt(minSlider.value), y1 = parseInt(maxSlider.value);
  if (y0 > y1) {
    if (document.activeElement === minSlider) { y1 = y0; maxSlider.value = y1; }
    else { y0 = y1; minSlider.value = y0; }
  }
  state.y0 = y0; state.y1 = y1;
  yearLabel.textContent = `${y0} – ${y1}`;

  const span = COUNTY_YEAR_MAX - COUNTY_YEAR_MIN || 1;
  const pctLo = (y0 - COUNTY_YEAR_MIN) / span * 100;
  const pctHi = (y1 - COUNTY_YEAR_MIN) / span * 100;
  rangeFill.style.left = pctLo + '%';
  rangeFill.style.width = (pctHi - pctLo) + '%';

  render();
}
minSlider.addEventListener('input', updateYears);
maxSlider.addEventListener('input', updateYears);
updateYears();

// ---- EXTERNAL LINKS ----
document.getElementById('link-eobrowser').href = 'https://browser.dataspace.copernicus.eu/?zoom=7&lat=45.94&lng=24.97';
document.getElementById('link-gfw').href = 'https://globalnaturewatch.org/map/country/ROU/';

// ---- INIT ----
renderDrivers();
setMode('map');
render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
