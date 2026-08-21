Romania Deforestation Map — package contents
==============================================

romania_deforestation_map.html
  The finished map. Open this file directly in any browser (double-click it,
  or drag it into a browser window). No installation or server needed —
  it's fully self-contained and pulls its map tiles and satellite imagery
  live from the internet when opened. Mobile-friendly: the layout adapts to
  phone-width screens automatically.

  Three view modes (top of the map — stacked on mobile, top right on
  desktop):
    - Map          County-by-county tree cover loss, color-coded (forest
                   green) by total hectares lost in the selected year
                   range. Drag the "Years" slider to change the range.
                   Click a county (or a bar in the ranking panel) to see
                   its year-by-year breakdown.
    - Satellite     Same choropleth overlay, on a satellite basemap instead
                   of the street map.
    - Compare imagery   Real before/after satellite photos (Sentinel-2,
                   2016-2025) for the same area, with a drag-to-reveal
                   divider. Pick the "Before" and "After" years from the
                   dropdowns, pan/zoom to any county, and drag the white
                   divider left/right to compare. County boundaries are
                   drawn on both sides of the divider so you can orient
                   yourself.

  The sidebar's "Why the forest is disappearing" section shows each cause
  as a percentage of total tracked loss (not a bar) — logging is such a
  dominant cause (96%+) that bars scaled to it made every other cause's
  bar invisible.

build_deforestation_map.py
  The Python script that generates romania_deforestation_map.html from the
  two data files below. Re-run it any time the underlying data is updated:

    python3 build_deforestation_map.py \
      --geojson romania-counties-simplified.geojson \
      --csv gfw_romania_county_loss.csv \
      --out romania_deforestation_map.html

gfw_romania_county_loss.csv
  Tree cover loss by Romanian county (județ) and year, 2001-2024, in
  hectares. Sourced from the Hansen/UMD/Google/USGS/NASA Global Forest
  Change dataset (>=30% canopy density threshold) via the public Global
  Nature Watch (formerly Global Forest Watch) data API. County IDs (adm1)
  match the ID_1 field in the GeoJSON file.

romania-counties-simplified.geojson
  Romania's 42 county boundaries (GADM v3.6, admin level 1), simplified
  for fast loading in the browser.

Data sources & credit
  - Tree cover loss: Hansen/UMD/Google/USGS/NASA Global Forest Change,
    via Global Nature Watch (globalnaturewatch.org), CC BY 4.0.
  - Loss driver classification: WRI/Google.
  - County boundaries: GADM v3.6.
  - Compare-imagery photos: Sentinel-2 cloudless annual mosaics by EOX IT
    Services GmbH (contains modified Copernicus Sentinel data), CC BY-SA 4.0.

Data fetched 2026-08-20. Global Nature Watch updates its loss figures
annually, so exact numbers may shift slightly in future years.
