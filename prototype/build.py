#!/usr/bin/env python3
"""Build the StatMaps single-file prototype.

Projects world country geometry (Equal Earth) to SVG path strings and embeds
World Bank indicator time-series (2000-2023) into template.html, producing
dist/statmaps-prototype.html — a fully self-contained interactive atlas.

Usage: python3 build.py <data_dir> [out_path]
  data_dir must contain countries.geo.json and wb_<CODE>.json files.
"""
import json
import math
import sys
from pathlib import Path

A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
M = math.sqrt(3) / 2

YEARS = list(range(2000, 2024))
EXCLUDE = {"ATA", "-99"}

DATASETS = [
    {"id": "population", "code": "SP.POP.TOTL", "title": "Population", "cat": "Population",
     "unit": "people", "fmt": "int", "ramp": "blue", "log": True,
     "desc": "Total population, all residents regardless of legal status or citizenship. Mid-year estimates."},
    {"id": "gdp-per-capita", "code": "NY.GDP.PCAP.CD", "title": "GDP per capita", "cat": "Economics",
     "unit": "current US$", "fmt": "usd", "ramp": "green", "log": True,
     "desc": "Gross domestic product divided by mid-year population, in current US dollars."},
    {"id": "life-expectancy", "code": "SP.DYN.LE00.IN", "title": "Life expectancy", "cat": "Health",
     "unit": "years at birth", "fmt": "num1", "ramp": "teal", "log": False,
     "desc": "Years a newborn would live if prevailing mortality patterns stayed constant."},
    {"id": "co2-per-capita", "code": "EN.GHG.CO2.PC.CE.AR5", "title": "CO₂ emissions per capita", "cat": "Environment",
     "unit": "t CO₂e / person", "fmt": "num2", "ramp": "orange", "log": True,
     "desc": "Carbon dioxide emissions per person, excluding land use change and forestry (AR5)."},
    {"id": "internet-users", "code": "IT.NET.USER.ZS", "title": "Internet users", "cat": "Lifestyle",
     "unit": "% of population", "fmt": "pct", "ramp": "purple", "log": False,
     "desc": "Share of individuals who used the internet in the last three months."},
    {"id": "renewable-energy", "code": "EG.FEC.RNEW.ZS", "title": "Renewable energy share", "cat": "Energy",
     "unit": "% of final energy", "fmt": "pct", "ramp": "green", "log": False,
     "desc": "Renewable energy consumption as a share of total final energy consumption."},
    {"id": "urban-population", "code": "SP.URB.TOTL.IN.ZS", "title": "Urban population", "cat": "Population",
     "unit": "% of population", "fmt": "pct", "ramp": "purple", "log": False,
     "desc": "Share of people living in urban areas as defined by national statistical offices."},
    {"id": "fertility-rate", "code": "SP.DYN.TFRT.IN", "title": "Fertility rate", "cat": "Population",
     "unit": "births per woman", "fmt": "num2", "ramp": "orange", "log": False,
     "desc": "Total fertility rate: births a woman would have under current age-specific rates."},
    {"id": "unemployment", "code": "SL.UEM.TOTL.ZS", "title": "Unemployment", "cat": "Economics",
     "unit": "% of labour force", "fmt": "pct", "ramp": "orange", "log": False,
     "desc": "Share of the labour force without work but available and seeking employment (ILO model)."},
    {"id": "forest-area", "code": "AG.LND.FRST.ZS", "title": "Forest area", "cat": "Environment",
     "unit": "% of land area", "fmt": "pct", "ramp": "green", "log": False,
     "desc": "Land under natural or planted trees of at least 5 m, whether productive or not."},
    {"id": "birth-rate", "code": "SP.DYN.CBRT.IN", "title": "Birth rate", "cat": "Population",
     "unit": "births per 1,000 people", "fmt": "num1", "ramp": "orange", "log": False,
     "desc": "Crude birth rate: live births per 1,000 mid-year population."},
    {"id": "population-65", "code": "SP.POP.65UP.TO.ZS", "title": "Population aged 65+", "cat": "Population",
     "unit": "% of population", "fmt": "pct", "ramp": "purple", "log": False,
     "desc": "Share of the population aged 65 and above."},
    {"id": "population-density", "code": "EN.POP.DNST", "title": "Population density", "cat": "Population",
     "unit": "people per km²", "fmt": "num1", "ramp": "blue", "log": True,
     "desc": "Mid-year population divided by land area in square kilometres."},
    {"id": "child-mortality", "code": "SH.DYN.MORT", "title": "Under-5 mortality", "cat": "Health",
     "unit": "per 1,000 live births", "fmt": "num1", "ramp": "orange", "log": True,
     "desc": "Probability per 1,000 that a newborn dies before reaching age five."},
    {"id": "health-spending", "code": "SH.XPD.CHEX.GD.ZS", "title": "Health spending", "cat": "Health",
     "unit": "% of GDP", "fmt": "num1", "ramp": "teal", "log": False,
     "desc": "Current health expenditure as a share of GDP."},
    {"id": "overweight-adults", "code": "SH.STA.OWAD.ZS", "title": "Overweight adults", "cat": "Health",
     "unit": "% of adults", "fmt": "pct", "ramp": "purple", "log": False,
     "desc": "Prevalence of overweight (BMI ≥ 25) among adults, both sexes."},
    {"id": "education-spending", "code": "SE.XPD.TOTL.GD.ZS", "title": "Education spending", "cat": "Education & Science",
     "unit": "% of GDP", "fmt": "num1", "ramp": "teal", "log": False,
     "desc": "General government expenditure on education as a share of GDP."},
    {"id": "rd-spending", "code": "GB.XPD.RSDV.GD.ZS", "title": "R&D expenditure", "cat": "Education & Science",
     "unit": "% of GDP", "fmt": "num2", "ramp": "blue", "log": False,
     "desc": "Gross domestic expenditure on research and development as a share of GDP. Sparse coverage outside OECD."},
    {"id": "military-spending", "code": "MS.MIL.XPND.GD.ZS", "title": "Military spending", "cat": "Politics",
     "unit": "% of GDP", "fmt": "num2", "ramp": "orange", "log": False,
     "desc": "Military expenditure as a share of GDP (SIPRI, via World Bank)."},
    {"id": "trade-openness", "code": "NE.TRD.GNFS.ZS", "title": "Trade openness", "cat": "Economics",
     "unit": "trade as % of GDP", "fmt": "pct", "ramp": "blue", "log": False,
     "desc": "Sum of exports and imports of goods and services as a share of GDP."},
    {"id": "inflation", "code": "FP.CPI.TOTL.ZG", "title": "Inflation", "cat": "Economics",
     "unit": "% annual (CPI)", "fmt": "num1", "ramp": "orange", "log": False,
     "desc": "Annual consumer price inflation. Negative values indicate deflation."},
    {"id": "electricity-access", "code": "EG.ELC.ACCS.ZS", "title": "Access to electricity", "cat": "Energy",
     "unit": "% of population", "fmt": "pct", "ramp": "teal", "log": False,
     "desc": "Share of the population with access to electricity."},
    {"id": "mobile-subscriptions", "code": "IT.CEL.SETS.P2", "title": "Mobile subscriptions", "cat": "Lifestyle",
     "unit": "per 100 people", "fmt": "num1", "ramp": "purple", "log": False,
     "desc": "Mobile cellular subscriptions per 100 people; can exceed 100 with multiple SIMs."},
    {"id": "female-labor", "code": "SL.TLF.CACT.FE.ZS", "title": "Female labour participation", "cat": "Economics",
     "unit": "% of women 15+", "fmt": "pct", "ramp": "green", "log": False,
     "desc": "Share of women aged 15+ participating in the labour force (ILO model)."},
    {"id": "tourist-arrivals", "code": "ST.INT.ARVL", "title": "Tourist arrivals", "cat": "Lifestyle",
     "unit": "arrivals per year", "fmt": "int", "ramp": "blue", "log": True,
     "desc": "International inbound tourist arrivals. Series ends 2020 in this extract."},
    {"id": "agricultural-land", "code": "AG.LND.AGRI.ZS", "title": "Agricultural land", "cat": "Environment",
     "unit": "% of land area", "fmt": "pct", "ramp": "green", "log": False,
     "desc": "Share of land area that is arable, under permanent crops, or permanent pasture."},
]


def equal_earth(lon, lat):
    lam, phi = math.radians(lon), math.radians(lat)
    theta = math.asin(M * math.sin(phi))
    t2 = theta * theta
    t6 = t2 * t2 * t2
    x = lam * math.cos(theta) / (M * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)))
    y = theta * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))
    return x, -y  # SVG y grows downward


def ring_to_path(ring, tx):
    pts = [tx(*equal_earth(lon, lat)) for lon, lat in ring]
    # drop consecutive duplicates after rounding
    out, prev = [], None
    for p in pts:
        if p != prev:
            out.append(p)
            prev = p
    if len(out) < 3:
        return ""
    return "M" + "L".join(f"{x},{y}" for x, y in out) + "Z"


def sig(v, n=4):
    if v == 0:
        return 0
    from decimal import Decimal
    r = round(v, -int(math.floor(math.log10(abs(v)))) + (n - 1))
    if abs(r) >= 10 ** (n - 1) or r == int(r):
        return int(r)
    return float(f"{r:.10g}")


def main():
    data_dir = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / "dist" / "statmaps-prototype.html"

    geo = json.loads((data_dir / "countries.geo.json").read_text())
    feats = [f for f in geo["features"] if f.get("id") not in EXCLUDE]

    # projection extents -> fit to 1000 x H canvas
    xs, ys = [], []
    for f in feats:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            for lon, lat in poly[0]:
                x, y = equal_earth(lon, lat)
                xs.append(x)
                ys.append(y)
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    W = 1000.0
    s = W / (maxx - minx)
    H = round((maxy - miny) * s, 1)

    def tx(x, y):
        return (round((x - minx) * s, 1), round((y - miny) * s, 1))

    paths, names = {}, {}
    for f in feats:
        iso = f["id"]
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        d = "".join(ring_to_path(ring, tx) for poly in polys for ring in poly)
        if d:
            paths[iso] = d
            names[iso] = f["properties"]["name"]

    iso_set = set(paths)
    values = {}
    for ds in DATASETS:
        raw = json.loads((data_dir / f"wb_{ds['code']}.json").read_text())
        rows = raw[1] or []
        per = {}
        for r in rows:
            iso, v, yr = r.get("countryiso3code"), r.get("value"), r.get("date")
            if v is None or iso not in iso_set:
                continue
            per.setdefault(iso, [None] * len(YEARS))
            yi = int(yr) - YEARS[0]
            if 0 <= yi < len(YEARS):
                per[iso][yi] = sig(v)
        values[ds["id"]] = per

    meta = [{k: ds[k] for k in ("id", "title", "cat", "unit", "fmt", "ramp", "log", "desc")} for ds in DATASETS]
    payload = {
        "H": H, "years": YEARS, "names": names, "paths": paths,
        "datasets": meta, "values": values,
        "source": {"name": "World Bank Open Data", "licence": "CC BY 4.0",
                   "url": "https://data.worldbank.org", "retrieved": "2026-07-16"},
    }
    blob = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    template = (Path(__file__).parent / "template.html").read_text()
    html = template.replace("/*__STATMAPS_DATA__*/null", blob)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    print(f"wrote {out_path} ({out_path.stat().st_size/1024:.0f} KB, {len(paths)} countries, "
          f"{sum(len(v) for v in values.values())} country-series)")


if __name__ == "__main__":
    main()
