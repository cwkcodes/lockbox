#!/usr/bin/env python3
"""StatMaps Phase 1 ETL — loads the prototype's fetched source files into PostGIS.

Reuses the dataset metadata definitions from prototype/build.py (hand-curated
DATASETS plus the declarative BULK_CODES connector), then loads:
  regions + geometries  <- countries.geo.json
  datasets + layers     <- metadata
  observations          <- wb_*.json / owid_*.csv / bigmac.csv
  features              <- usgs_quakes.json, powerplants.csv, unesco_wd.json

Zero Python dependencies: rows are streamed to `psql \\copy` via stdin.

Usage:
  DATABASE_URL=postgres://statmaps@127.0.0.1:5544/statmaps \\
      python3 load.py <data_dir>
"""
import csv
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "prototype"))
from build import DATASETS, YEARS, build_bulk_datasets  # noqa: E402

DB = os.environ.get("DATABASE_URL", "postgres://statmaps@127.0.0.1:5544/statmaps")
EXCLUDE = {"ATA", "-99"}


def psql(sql, stdin=None):
    r = subprocess.run(["psql", DB, "-v", "ON_ERROR_STOP=1", "-q", "-c", sql],
                       input=stdin, text=True, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"psql failed: {sql[:80]}…\n{r.stderr}")
    return r.stdout


def copy(table_cols, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    for row in rows:
        w.writerow(row)
    psql(f"\\copy {table_cols} FROM STDIN WITH (FORMAT csv)", stdin=buf.getvalue())


def esc(s):
    return s.replace("'", "''")


def main():
    data_dir = Path(sys.argv[1])
    geo = json.loads((data_dir / "countries.geo.json").read_text())
    feats = [f for f in geo["features"] if f.get("id") not in EXCLUDE]
    iso_set = {f["id"] for f in feats}

    psql("""INSERT INTO licences (licence_id, name, url, attribution_text) VALUES
        ('cc-by-4.0','CC BY 4.0','https://creativecommons.org/licenses/by/4.0/','See per-dataset source'),
        ('cc0','CC0 / Public domain','https://creativecommons.org/publicdomain/zero/1.0/',''),
        ('open-misc','Open (see source)','', 'See per-dataset source')
        ON CONFLICT DO NOTHING""")

    # sources: one row per distinct provider named in dataset metadata
    all_ds = DATASETS + build_bulk_datasets(data_dir, iso_set)
    default_src = ("world-bank", "World Bank Open Data", "https://data.worldbank.org", "cc-by-4.0")
    srcs = {default_src[0]: default_src,
            "natural-earth": ("natural-earth", "Natural Earth / OSM-derived boundaries", "https://www.naturalearthdata.com", "cc0"),
            "usgs": ("usgs", "USGS Earthquake Catalog", "https://earthquake.usgs.gov", "cc0"),
            "wri": ("wri", "WRI Global Power Plant Database", "https://datasets.wri.org", "cc-by-4.0"),
            "wikidata": ("wikidata", "Wikidata", "https://www.wikidata.org", "cc0")}
    for ds in all_ds:
        if "src" in ds:
            sid = re.sub(r"[^a-z0-9]+", "-", ds["src"]["name"].lower()).strip("-")[:40]
            lic = "cc-by-4.0" if "CC BY" in ds["src"]["licence"] else "open-misc"
            srcs[sid] = (sid, ds["src"]["name"], ds["src"]["url"], lic)
            ds["_sid"] = sid
        else:
            ds["_sid"] = "world-bank"
    psql("INSERT INTO sources (source_id,name,url,licence_id) VALUES " +
         ",".join(f"('{esc(a)}','{esc(b)}','{esc(c)}','{d}')" for a, b, c, d in srcs.values()) +
         " ON CONFLICT DO NOTHING")

    # regions + geometries
    copy("regions (region_id, kind, iso_a3, name)",
         ((f"iso:{f['id']}", "country", f["id"], f["properties"]["name"]) for f in feats))
    copy("region_geometries (region_id, geom, source_id)",
         ((f"iso:{f['id']}",
           json.dumps(f["geometry"] if f["geometry"]["type"] == "MultiPolygon" else
                      {"type": "MultiPolygon", "coordinates": [f["geometry"]["coordinates"]]}),
           "natural-earth") for f in feats))
    psql("UPDATE region_geometries SET geom = ST_SetSRID(geom, 4326) WHERE ST_SRID(geom) = 0")

    # datasets + layers + observations
    n_obs = 0
    for ds in all_ds:
        rows = load_observations(ds, data_dir, iso_set)
        if not rows:
            continue
        years = [y for _, y, _ in rows]
        lic = "cc-by-4.0" if "src" not in ds or "CC BY" in ds["src"]["licence"] else "open-misc"
        psql(f"""INSERT INTO datasets (dataset_id, source_id, licence_id, title, description,
                 unit, category, time_min, time_max)
                 VALUES ('{ds['id']}','{ds['_sid']}','{lic}','{esc(ds['title'])}',
                 '{esc(ds['desc'])}','{esc(ds['unit'])}','{esc(ds['cat'])}',
                 {min(years)},{max(years)})""")
        psql(f"""INSERT INTO layers (layer_id, dataset_id, title, geometry_kind, default_style)
                 VALUES ('{ds['id']}','{ds['id']}','{esc(ds['title'])}','choropleth',
                 '{json.dumps({"ramp": ds["ramp"], "log": ds["log"], "fmt": ds["fmt"]})}')""")
        copy("observations (dataset_id, region_id, year, value)",
             ((ds["id"], f"iso:{iso}", y, v) for iso, y, v in rows))
        n_obs += len(rows)

    n_feat = load_features(data_dir, iso_set)
    print(f"loaded {len(feats)} regions, {n_obs} observations, {n_feat} features")


def load_observations(ds, data_dir, iso_set):
    """Return [(iso, year, value)] for one dataset (mirrors prototype loaders)."""
    rows = []
    loader = ds.get("loader")
    if loader == "owid":
        with open(data_dir / ds["file"], newline="") as fh:
            for r in csv.reader(fh):
                if not r or r[0] == "Entity" or not r[3] or r[1] not in iso_set:
                    continue
                y = int(r[2])
                if YEARS[0] <= y <= YEARS[-1]:
                    rows.append((r[1], y, float(r[3])))
    elif loader == "bigmac":
        from collections import defaultdict
        acc = defaultdict(list)
        with open(data_dir / ds["file"], newline="") as fh:
            for r in csv.DictReader(fh):
                if r["dollar_price"] and r["iso_a3"] in iso_set:
                    y = int(r["date"][:4])
                    if YEARS[0] <= y <= YEARS[-1]:
                        acc[(r["iso_a3"], y)].append(float(r["dollar_price"]))
        rows = [(i, y, sum(v) / len(v)) for (i, y), v in acc.items()]
    else:
        f = data_dir / f"wb_{ds['code']}.json"
        if not f.exists():
            return []
        raw = json.loads(f.read_text())
        for r in raw[1] or []:
            if r.get("value") is not None and r.get("countryiso3code") in iso_set:
                y = int(r["date"])
                if YEARS[0] <= y <= YEARS[-1]:
                    rows.append((r["countryiso3code"], y, r["value"]))
    return rows


def load_features(data_dir, iso_set):
    """Representative point layers: earthquakes (event), power plants (static),
    UNESCO sites (cumulative). Remaining prototype point sets load identically."""
    from datetime import datetime, timezone
    total = 0

    def ds_row(did, sid, lic, title, cat, kind):
        psql(f"""INSERT INTO datasets (dataset_id, source_id, licence_id, title, category)
                 VALUES ('{did}','{sid}','{lic}','{esc(title)}','{cat}')""")
        psql(f"""INSERT INTO layers (layer_id, dataset_id, title, geometry_kind)
                 VALUES ('{did}','{did}','{esc(title)}','{kind}')""")

    q = json.loads((data_dir / "usgs_quakes.json").read_text())
    ds_row("earthquakes", "usgs", "cc0", "Earthquakes M6+", "Geography", "point")
    rows = []
    for f in q["features"]:
        lon, lat = f["geometry"]["coordinates"][:2]
        yr = datetime.fromtimestamp(f["properties"]["time"] / 1000, tz=timezone.utc).year
        rows.append(("earthquakes", f"SRID=4326;POINT({lon} {lat})", yr,
                     json.dumps({"mag": f["properties"]["mag"]})))
    copy("features (dataset_id, geom, year, properties)", rows)
    total += len(rows)

    ds_row("power-plants", "wri", "cc-by-4.0", "Power plants ≥ 1 GW", "Energy", "point")
    rows = []
    with open(data_dir / "powerplants.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            cap = float(r["capacity_mw"] or 0)
            if cap >= 1000:
                rows.append(("power-plants", f"SRID=4326;POINT({r['longitude']} {r['latitude']})", "",
                             json.dumps({"name": r["name"], "fuel": r["primary_fuel"], "gw": round(cap / 1000, 1)})))
    copy("features (dataset_id, geom, year, properties)", rows)
    total += len(rows)

    u = json.loads((data_dir / "unesco_wd.json").read_text())
    ds_row("unesco-sites", "wikidata", "cc0", "UNESCO World Heritage sites", "Entertainment & Culture", "point")
    seen, rows = set(), []
    for r in u["results"]["bindings"]:
        if r["item"]["value"] in seen:
            continue
        seen.add(r["item"]["value"])
        m = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", r["coord"]["value"])
        name = r.get("itemLabel", {}).get("value", "")
        if not m or not name or re.fullmatch(r"Q\d+", name):
            continue
        yr = r.get("year", {}).get("value", "")
        rows.append(("unesco-sites", f"SRID=4326;POINT({m.group(1)} {m.group(2)})", yr,
                     json.dumps({"name": name})))
    copy("features (dataset_id, geom, year, properties)", rows)
    return total + len(rows)


if __name__ == "__main__":
    main()
