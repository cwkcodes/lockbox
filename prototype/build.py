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
    {"id": "gini", "code": "SI.POV.GINI", "title": "Income inequality (Gini)", "cat": "Economics",
     "unit": "Gini index (0 = equal)", "fmt": "num1", "ramp": "purple", "log": False,
     "desc": "Gini index of income distribution. Survey-based; sparse in some years — scrub the timeline."},
    {"id": "homicide-rate", "code": "VC.IHR.PSRC.P5", "title": "Homicide rate", "cat": "Lifestyle",
     "unit": "per 100,000 people", "fmt": "num1", "ramp": "orange", "log": True,
     "desc": "Intentional homicides per 100,000 population (UNODC)."},
    {"id": "smoking", "code": "SH.PRV.SMOK", "title": "Smoking prevalence", "cat": "Health",
     "unit": "% of adults 15+", "fmt": "pct", "ramp": "blue", "log": False,
     "desc": "Share of adults who currently use any tobacco product, both sexes."},
    {"id": "alcohol", "code": "SH.ALC.PCAP.LI", "title": "Alcohol consumption", "cat": "Lifestyle",
     "unit": "litres pure alcohol per person 15+", "fmt": "num1", "ramp": "orange", "log": False,
     "desc": "Total (recorded plus estimated unrecorded) alcohol consumption per capita, age 15+."},
    {"id": "physicians", "code": "SH.MED.PHYS.ZS", "title": "Physicians density", "cat": "Health",
     "unit": "per 1,000 people", "fmt": "num2", "ramp": "teal", "log": False,
     "desc": "Medical doctors per 1,000 population, including generalists and specialists."},
    {"id": "air-passengers", "code": "IS.AIR.PSGR", "title": "Air passengers", "cat": "Lifestyle",
     "unit": "passengers carried per year", "fmt": "int", "ramp": "blue", "log": True,
     "desc": "Domestic and international passengers of air carriers registered in the country."},
    {"id": "gdp-growth", "code": "NY.GDP.MKTP.KD.ZG", "title": "GDP growth", "cat": "Economics",
     "unit": "% annual (real)", "fmt": "num1", "ramp": "green", "log": False,
     "desc": "Annual growth rate of real GDP. Negative values are recessions."},
    {"id": "fdi-inflows", "code": "BX.KLT.DINV.WD.GD.ZS", "title": "FDI inflows", "cat": "Economics",
     "unit": "% of GDP", "fmt": "num1", "ramp": "blue", "log": False,
     "desc": "Net inflows of foreign direct investment as a share of GDP."},
    {"id": "remittances", "code": "BX.TRF.PWKR.DT.GD.ZS", "title": "Remittances received", "cat": "Economics",
     "unit": "% of GDP", "fmt": "num1", "ramp": "purple", "log": False,
     "desc": "Personal remittances received from abroad as a share of GDP."},
    {"id": "population-growth", "code": "SP.POP.GROW", "title": "Population growth", "cat": "Population",
     "unit": "% annual", "fmt": "num2", "ramp": "orange", "log": False,
     "desc": "Annual population growth rate. Negative values indicate shrinking populations."},
    {"id": "co2-total", "code": "EN.GHG.CO2.MT.CE.AR5", "title": "CO₂ emissions (total)", "cat": "Environment",
     "unit": "Mt CO₂e per year", "fmt": "num1", "ramp": "orange", "log": True,
     "desc": "Total national carbon dioxide emissions, excluding LULUCF (AR5)."},
    {"id": "secondary-enrollment", "code": "SE.SEC.ENRR", "title": "Secondary school enrolment", "cat": "Education & Science",
     "unit": "% gross", "fmt": "pct", "ramp": "teal", "log": False,
     "desc": "Secondary enrolment as a share of the official secondary-age population; can exceed 100%."},
    {"id": "sanitation", "code": "SH.STA.BASS.ZS", "title": "Basic sanitation access", "cat": "Health",
     "unit": "% of population", "fmt": "pct", "ramp": "green", "log": False,
     "desc": "Share of the population using at least basic sanitation services."},
    {"id": "armed-forces", "code": "MS.MIL.TOTL.TF.ZS", "title": "Armed forces personnel", "cat": "Politics",
     "unit": "% of labour force", "fmt": "num2", "ramp": "orange", "log": False,
     "desc": "Active-duty military and paramilitary personnel as a share of the labour force."},
    {"id": "happiness", "loader": "owid", "file": "owid_happiness.csv", "title": "Life satisfaction", "cat": "Lifestyle",
     "unit": "Cantril ladder (0–10)", "fmt": "num2", "ramp": "teal", "log": False,
     "src": {"name": "World Happiness Report via Our World in Data", "licence": "CC BY 4.0",
             "url": "https://ourworldindata.org/grapher/happiness-cantril-ladder"},
     "desc": "Self-reported life satisfaction: national average answer to the Cantril ladder question (0 = worst possible life, 10 = best). Survey series begins 2011."},
    {"id": "democracy-index", "loader": "owid", "file": "owid_democracy.csv", "title": "Electoral democracy index", "cat": "Politics",
     "unit": "V-Dem index (0–1)", "fmt": "num2", "ramp": "blue", "log": False,
     "src": {"name": "V-Dem via Our World in Data", "licence": "CC BY 4.0",
             "url": "https://ourworldindata.org/grapher/electoral-democracy-index"},
     "desc": "V-Dem electoral democracy index: free and fair elections, suffrage, and freedoms of expression and association. Expert-coded, 0–1."},
    {"id": "women-parliament", "code": "SG.GEN.PARL.ZS", "title": "Women in parliament", "cat": "Politics",
     "unit": "% of seats", "fmt": "pct", "ramp": "purple", "log": False,
     "desc": "Share of seats held by women in national parliaments (single or lower chamber)."},
    {"id": "literacy", "code": "SE.ADT.LITR.ZS", "title": "Adult literacy", "cat": "Education & Science",
     "unit": "% of people 15+", "fmt": "pct", "ramp": "teal", "log": False,
     "desc": "Share of adults who can read and write. Census/survey-based — sparse for high-income countries, which rarely measure it."},
    {"id": "extreme-poverty", "code": "SI.POV.DDAY", "title": "Extreme poverty", "cat": "Economics",
     "unit": "% below $2.15/day (2017 PPP)", "fmt": "pct", "ramp": "orange", "log": False,
     "desc": "Share of the population living below the international extreme poverty line."},
    {"id": "electricity-use", "code": "EG.USE.ELEC.KH.PC", "title": "Electricity use per capita", "cat": "Energy",
     "unit": "kWh per person per year", "fmt": "int", "ramp": "blue", "log": True,
     "desc": "Electric power consumption per capita. IEA-sourced series; ends mid-2010s for many countries."},
    {"id": "patents", "code": "IP.PAT.RESD", "title": "Patent applications", "cat": "Education & Science",
     "unit": "resident applications per year", "fmt": "int", "ramp": "purple", "log": True,
     "desc": "Patent applications filed by residents with the national patent office (WIPO)."},
    {"id": "hightech-exports", "code": "TX.VAL.TECH.MF.ZS", "title": "High-tech exports", "cat": "Economics",
     "unit": "% of manufactured exports", "fmt": "pct", "ramp": "blue", "log": False,
     "desc": "High-technology products as a share of manufactured exports."},
    {"id": "tax-revenue", "code": "GC.TAX.TOTL.GD.ZS", "title": "Tax revenue", "cat": "Economics",
     "unit": "% of GDP", "fmt": "num1", "ramp": "green", "log": False,
     "desc": "Central government tax revenue as a share of GDP."},
    {"id": "age-dependency", "code": "SP.POP.DPND", "title": "Age dependency ratio", "cat": "Population",
     "unit": "dependents per 100 working-age", "fmt": "num1", "ramp": "orange", "log": False,
     "desc": "People younger than 15 or older than 64 relative to the working-age population."},
    {"id": "exports", "code": "NE.EXP.GNFS.ZS", "title": "Exports", "cat": "Economics",
     "unit": "% of GDP", "fmt": "pct", "ramp": "green", "log": False,
     "desc": "Exports of goods and services as a share of GDP."},
    {"id": "schooling", "loader": "owid", "file": "owid_average-years-of-schooling.csv", "title": "Years of schooling", "cat": "Education & Science",
     "unit": "average years, adults 25+", "fmt": "num1", "ramp": "teal", "log": False,
     "src": {"name": "UNDP HDR via Our World in Data", "licence": "CC BY 4.0",
             "url": "https://ourworldindata.org/grapher/average-years-of-schooling"},
     "desc": "Average years of formal education completed by adults aged 25 and over."},
    {"id": "working-hours", "loader": "owid", "file": "owid_annual-working-hours-per-worker.csv", "title": "Annual working hours", "cat": "Economics",
     "unit": "hours per worker per year", "fmt": "int", "ramp": "orange", "log": False,
     "src": {"name": "Penn World Table via Our World in Data", "licence": "CC BY 4.0",
             "url": "https://ourworldindata.org/grapher/annual-working-hours-per-worker"},
     "desc": "Average annual hours actually worked per employed person."},
    {"id": "calories", "loader": "owid", "file": "owid_daily-per-capita-caloric-supply.csv", "title": "Daily calorie supply", "cat": "Lifestyle",
     "unit": "kcal per person per day", "fmt": "int", "ramp": "green", "log": False,
     "src": {"name": "FAO via Our World in Data", "licence": "CC BY 4.0",
             "url": "https://ourworldindata.org/grapher/daily-per-capita-caloric-supply"},
     "desc": "Food supply available for consumption, after exports and waste at the retail level."},
    {"id": "ev-share", "loader": "owid", "file": "owid_electric-car-sales-share.csv", "title": "Electric car sales share", "cat": "Energy",
     "unit": "% of new cars sold", "fmt": "pct", "ramp": "teal", "log": False,
     "src": {"name": "IEA Global EV Outlook via Our World in Data", "licence": "CC BY 4.0",
             "url": "https://ourworldindata.org/grapher/electric-car-sales-share"},
     "desc": "Battery-electric and plug-in hybrid cars as a share of new car sales. Series begins 2011, major markets only."},
    {"id": "beer", "loader": "owid", "file": "owid_beer-consumption-per-person.csv", "title": "Beer consumption", "cat": "Lifestyle",
     "unit": "L pure alcohol per person 15+ (beer)", "fmt": "num1", "ramp": "orange", "log": False,
     "src": {"name": "WHO GHO via Our World in Data", "licence": "CC BY 4.0",
             "url": "https://ourworldindata.org/grapher/beer-consumption-per-person"},
     "desc": "Recorded beer consumption, expressed as litres of pure alcohol per adult per year."},
    {"id": "wine", "loader": "owid", "file": "owid_wine-consumption-per-capita.csv", "title": "Wine consumption", "cat": "Lifestyle",
     "unit": "L pure alcohol per person 15+ (wine)", "fmt": "num2", "ramp": "purple", "log": False,
     "src": {"name": "WHO GHO via Our World in Data", "licence": "CC BY 4.0",
             "url": "https://ourworldindata.org/grapher/wine-consumption-per-capita"},
     "desc": "Recorded wine consumption, expressed as litres of pure alcohol per adult per year."},
    {"id": "meat", "loader": "owid", "file": "owid_meat-supply-per-person.csv", "title": "Meat supply", "cat": "Lifestyle",
     "unit": "kg per person per year", "fmt": "num1", "ramp": "orange", "log": False,
     "src": {"name": "FAO via Our World in Data", "licence": "CC BY 4.0",
             "url": "https://ourworldindata.org/grapher/meat-supply-per-person"},
     "desc": "Meat available for consumption per person, carcass-weight equivalent."},
]

POINT_LAYERS = [
    {"id": "earthquakes", "title": "Earthquakes M6+", "cat": "Geography", "mode": "year",
     "unit": "moment magnitude", "color": "#E88B3A", "shape": "circle",
     "src": {"name": "USGS Earthquake Catalog", "licence": "Public domain",
             "url": "https://earthquake.usgs.gov/fdsnws/event/1/"},
     "desc": "All magnitude ≥ 6.0 earthquakes, 2000–2023. The timeline shows one year at a time; symbol size scales with magnitude."},
    {"id": "volcanoes", "title": "Volcanoes (Holocene)", "cat": "Geography", "mode": "static",
     "unit": "volcano", "color": "#D64550", "shape": "triangle",
     "src": {"name": "Smithsonian Global Volcanism Program", "licence": "Free with attribution",
             "url": "https://volcano.si.edu"},
     "desc": "Volcanoes with confirmed or suspected Holocene eruptions. Static layer — not affected by the timeline."},
    {"id": "unesco-sites", "title": "UNESCO World Heritage sites", "cat": "Entertainment & Culture", "mode": "cumul",
     "unit": "site", "color": "#2B8A86", "shape": "circle",
     "src": {"name": "Wikidata", "licence": "CC0",
             "url": "https://www.wikidata.org"},
     "desc": "World Heritage sites with coordinates from Wikidata. The timeline shows sites inscribed up to the selected year; sites without a recorded inscription year are always shown."},
    {"id": "airports", "title": "Major airports", "cat": "Lifestyle", "mode": "static",
     "unit": "airport", "color": "#3572B0", "shape": "circle",
     "src": {"name": "OurAirports", "licence": "Public domain",
             "url": "https://ourairports.com/data/"},
     "desc": "Large airports with scheduled commercial service. Static layer."},
    {"id": "power-plants", "title": "Power plants ≥ 1 GW", "cat": "Energy", "mode": "static",
     "unit": "gigawatts", "color": "#E88B3A", "shape": "circle",
     "cats": [{"label": "Coal", "color": "#8A6B4D"}, {"label": "Gas", "color": "#E88B3A"},
              {"label": "Hydro", "color": "#3572B0"}, {"label": "Nuclear", "color": "#9C7AC0"},
              {"label": "Oil", "color": "#5C6B77"}, {"label": "Other", "color": "#57B0A8"}],
     "src": {"name": "WRI Global Power Plant Database", "licence": "CC BY 4.0",
             "url": "https://datasets.wri.org/dataset/globalpowerplantdatabase"},
     "desc": "Power stations of one gigawatt or more, coloured by primary fuel and sized by capacity. Snapshot database (2021) — recent plants are missing."},
    {"id": "cities", "title": "Cities over 1 million", "cat": "Population", "mode": "static",
     "unit": "people (urban agglomeration)", "color": "#7450A0", "shape": "circle",
     "src": {"name": "Natural Earth populated places", "licence": "Public domain",
             "url": "https://www.naturalearthdata.com"},
     "desc": "Urban agglomerations of at least one million people, sized by population."},
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
        per = {}
        if ds.get("loader") == "owid":
            import csv
            with open(data_dir / ds["file"], newline="") as fh:
                for r in csv.reader(fh):
                    if not r or r[0] == "Entity":
                        continue
                    iso, yr, v = r[1], r[2], r[3]
                    if not v or iso not in iso_set:
                        continue
                    yi = int(yr) - YEARS[0]
                    if 0 <= yi < len(YEARS):
                        per.setdefault(iso, [None] * len(YEARS))[yi] = sig(float(v))
        else:
            raw = json.loads((data_dir / f"wb_{ds['code']}.json").read_text())
            for r in raw[1] or []:
                iso, v, yr = r.get("countryiso3code"), r.get("value"), r.get("date")
                if v is None or iso not in iso_set:
                    continue
                yi = int(yr) - YEARS[0]
                if 0 <= yi < len(YEARS):
                    per.setdefault(iso, [None] * len(YEARS))[yi] = sig(v)
        values[ds["id"]] = per

    def project(lon, lat):
        return tx(*equal_earth(lon, lat))

    point_data = {}
    # earthquakes: [x, y, year, magnitude]
    from datetime import datetime, timezone
    q = json.loads((data_dir / "usgs_quakes.json").read_text())
    pts = []
    for f in q["features"]:
        lon, lat = f["geometry"]["coordinates"][:2]
        yr = datetime.fromtimestamp(f["properties"]["time"] / 1000, tz=timezone.utc).year
        if YEARS[0] <= yr <= YEARS[-1]:
            x, y = project(lon, lat)
            pts.append([x, y, yr, round(f["properties"]["mag"], 1)])
    point_data["earthquakes"] = pts

    # volcanoes: [x, y, name, country, last_eruption_year|null]
    v = json.loads((data_dir / "volcanoes.json").read_text())
    pts = []
    for f in v["features"]:
        lon, lat = f["geometry"]["coordinates"][:2]
        p = f["properties"]
        x, y = project(lon, lat)
        pts.append([x, y, p["Volcano_Name"], p.get("Country") or "", p.get("Last_Eruption_Year")])
    point_data["volcanoes"] = pts

    # unesco: [x, y, inscription_year|0, name]  (dedupe by wikidata item)
    import re
    u = json.loads((data_dir / "unesco_wd.json").read_text())
    seen, pts = {}, []
    for r in u["results"]["bindings"]:
        item = r["item"]["value"]
        if item in seen:
            continue
        seen[item] = True
        m = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", r["coord"]["value"])
        if not m:
            continue
        lon, lat = float(m.group(1)), float(m.group(2))
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            continue
        name = r.get("itemLabel", {}).get("value", "")
        if not name or re.fullmatch(r"Q\d+", name):
            continue
        yr = int(r["year"]["value"]) if "year" in r else 0
        x, y = project(lon, lat)
        pts.append([x, y, yr, name])
    point_data["unesco-sites"] = pts

    import csv as csvmod
    # airports: [x, y, name]
    pts = []
    with open(data_dir / "airports.csv", newline="", encoding="utf-8") as fh:
        for r in csvmod.DictReader(fh):
            if r["type"] != "large_airport" or r["scheduled_service"] != "yes":
                continue
            x, y = project(float(r["longitude_deg"]), float(r["latitude_deg"]))
            name = r["name"]
            if r.get("municipality") and r["municipality"].lower() not in name.lower():
                name += f" ({r['municipality']})"
            pts.append([x, y, name])
    point_data["airports"] = pts

    # power plants >= 1 GW: [x, y, fuel_cat_index, capacity_gw, name]
    fuel_cat = {"Coal": 0, "Gas": 1, "Hydro": 2, "Nuclear": 3, "Oil": 4}
    pts = []
    with open(data_dir / "powerplants.csv", newline="", encoding="utf-8") as fh:
        for r in csvmod.DictReader(fh):
            cap = float(r["capacity_mw"] or 0)
            if cap < 1000:
                continue
            x, y = project(float(r["longitude"]), float(r["latitude"]))
            pts.append([x, y, fuel_cat.get(r["primary_fuel"], 5), round(cap / 1000, 1), r["name"]])
    point_data["power-plants"] = pts

    # cities >= 1M: [x, y, population_millions, name]
    c = json.loads((data_dir / "cities.geojson").read_text())
    pts = []
    for f in c["features"]:
        pop = f["properties"].get("pop_max") or 0
        if pop < 1_000_000:
            continue
        lon, lat = f["geometry"]["coordinates"][:2]
        x, y = project(lon, lat)
        pts.append([x, y, round(pop / 1e6, 1), f["properties"].get("name") or ""])
    point_data["cities"] = pts

    meta_keys = ("id", "title", "cat", "unit", "fmt", "ramp", "log", "desc")
    meta = [{**{k: ds[k] for k in meta_keys}, **({"src": ds["src"]} if "src" in ds else {})} for ds in DATASETS]
    pmeta = [{**{k: pl[k] for k in ("id", "title", "cat", "unit", "mode", "color", "shape", "desc", "src")},
              **({"cats": pl["cats"]} if "cats" in pl else {}),
              "count": len(point_data[pl["id"]])} for pl in POINT_LAYERS]
    payload = {
        "H": H, "years": YEARS, "names": names, "paths": paths,
        "datasets": meta, "values": values,
        "pointLayers": pmeta, "points": point_data,
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
