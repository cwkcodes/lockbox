# StatMaps Prototype

A single-file interactive atlas implementing the core loops of the [StatMaps specification](../statmaps-spec/README.md): search → layer → choropleth → timeline → share, plus Correlation Mode (spec 06-ai §4) and Discover.

## Contents

- `template.html` — all UI, styles, and logic; data is injected at the `/*__STATMAPS_DATA__*/` marker.
- `build.py` — fetch-time pipeline: projects country geometry (Equal Earth) to SVG path strings, compacts World Bank indicator series (2000–2023), and writes the self-contained page.
- `dist/statmaps-prototype.html` — generated output (committed for convenience).

## Build

```bash
# 1. Fetch source data into a directory:
#    countries.geo.json  (https://github.com/johan/world.geo.json)
#    wb_<CODE>.json      (https://api.worldbank.org/v2/country/all/indicator/<CODE>?format=json&per_page=20000&date=2000:2023)
#    for every code listed in DATASETS inside build.py, plus:
#    owid_happiness.csv / owid_democracy.csv  (https://ourworldindata.org/grapher/<slug>.csv)
#    usgs_quakes.json    (USGS FDSN event API, minmagnitude=6, 2000-2023)
#    volcanoes.json      (Smithsonian GVP WFS, Holocene volcano list)
#    unesco_wd.json      (Wikidata SPARQL: items with P757 + P625 + P1435=Q9259)
# 2. Build:
python3 build.py <data_dir> [out_path]
```

## What it implements from the spec

| Spec feature | Prototype implementation |
|---|---|
| Layer system (01-product §2.3) | 42 choropleth layers, quintile classification (log-transformed where flagged), 5-step sequential ramps, multiply-blend overlay |
| Point/event layers (03-architecture §5) | USGS earthquakes M6+ (per-year, magnitude-sized), Smithsonian Holocene volcanoes (static), UNESCO World Heritage sites via Wikidata (cumulative by inscription year) |
| Multi-source provenance (02-data) | Per-dataset source and licence (World Bank, OWID/V-Dem, OWID/WHR, USGS, Smithsonian GVP, Wikidata) surfaced in legend, detail panel, and about dialogs |
| Timeline (§2.4) | 2000–2023 scrubber with playback; choropleth reclassifies per year |
| URL state (§2.8) | Layer, overlay, year, viewport, and selected country encoded in the URL hash |
| Detail panel (§2.5) | Value, world rank, sparkline, 26-indicator profile, provenance |
| Correlation Mode (06-ai §4) | Client-side Spearman ρ, BH-FDR correction, partial ρ controlling log GDP per capita, tier labels, scatter view, non-causal language |
| Discover (10-review §1) | Data-verified fact generator (top-of-world, fastest riser, hidden link) |
| Provenance (README principle 2) | Source, licence, retrieval date, classification method on every layer |

## Deliberate deviations

Runs without a server or external requests (artifact CSP), so it uses precomputed SVG geometry instead of the MapLibre vector-tile stack — zoom is world-to-country level. Data: World Bank Open Data (CC BY 4.0); boundaries: Natural Earth / OSM-derived (johan/world.geo.json).
