# Harta defrișărilor din România

Interactive map of tree cover loss across Romania's 42 counties (județe), 2001–2025 —
inspired by [Global Forest Watch](https://globalforestwatch.org) and by the well-documented
illegal logging in Romania's Carpathian old-growth forests, wanting a version that also
lets you see the actual satellite imagery, not just the data.

🔗 **[Live map](https://dana-juncu.github.io/ro-deforestation-map/romania_deforestation_map.html)**

## What's in the map

- **Choropleth by județ** — total tree cover lost, color-coded, for any year range you
  pick with the slider (2001–2024)
- **Three view modes** — street map, satellite basemap, and **Compare imagery**: real
  Sentinel-2 photos with a drag-to-reveal before/after divider (2016–2025), so you can
  see forest actually disappear between two chosen years, not just a colored overlay
- **County ranking** — top 10 counties by loss in the selected range, click-through to
  a year-by-year popup for any county
- **Why the forest is disappearing** — national loss broken down by cause (logging,
  agriculture, wildfire, etc.), as a share of total
- **National trend** — total hectares lost per year, 2001–2025
- **RO / EN language toggle** — every label, popup, and number switches language and locale
  formatting (Romanian uses `.` as the thousands separator, English uses `,`)
- Mobile-friendly layout

Single self-contained `romania_deforestation_map.html` — Leaflet loaded from CDN, all
county boundary and loss data embedded inline, no build step or server required to view
it. `build_deforestation_map.py` regenerates that file from the two data files below,
if the source data is ever refreshed.

## Data sources

- **Global Nature Watch** (formerly Global Forest Watch) — Hansen/UMD/Google/USGS/NASA
  Global Forest Change dataset, ≥30% canopy density threshold: county-level and
  national tree cover loss by year, plus loss-driver classification (WRI/Google), via
  their public data API.
- **GADM v3.6** — county (admin-1) boundaries.
- **EOX IT Services GmbH** — Sentinel-2 cloudless annual mosaics, 2016–2025, the real
  satellite photography behind Compare-imagery mode. CC BY-SA 4.0.

## Data files

| File | Contents |
|---|---|
| `gfw_romania_county_loss.csv` | Tree cover loss by county (județ) and year, 2001–2024, in hectares |
| `romania-counties-simplified.geojson` | Romania's 42 county boundaries (GADM v3.6), simplified for fast loading |
| `build_deforestation_map.py` | Python script that regenerates the HTML map from the two files above |

## Known limitations

- County-level, not pixel-level — the choropleth shows which counties lost the most,
  not exactly where within them (Compare-imagery mode lets you inspect any specific
  area visually instead).
- "Tree cover loss" isn't the same as permanent deforestation — the Hansen dataset
  flags any loss above the canopy-density threshold, including legal harvest cycles in
  managed forest, not only permanent land-use conversion.
- The loss-driver breakdown (why the forest is disappearing) is national-only in the
  source data — it can't be joined to the choropleth by county.
- Compare-imagery mode uses annual cloud-free mosaics, not same-day photos — seasonal
  or lighting differences between the two chosen years can look like change even where
  none occurred.
- 2025 is included in the national trend chart but not yet broken out by county —
  2024 is the latest year with a full per-county breakdown in the source data.

## License

Code: MIT. Data: subject to the terms of the original sources (Global Nature
Watch / Hansen-UMD-Google-USGS-NASA, GADM, EOX IT Services) — this repo just
aggregates and republishes what they've already made public.
