"""Central configuration for the v0.1 pipeline (EPL, 2014-15 onwards, 1X2 + double chance)."""
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent.parent
DATA_DIR = PROJECT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "football.sqlite"
REPORTS_DIR = PROJECT_DIR / "reports"

LEAGUE_CODE = "E0"  # football-data.co.uk code for the English Premier League
COMPETITION_ID = "ENG-PL"

# football-data.co.uk encodes seasons as e.g. 1415 for 2014-15.
FIRST_SEASON_START_YEAR = 2014
LAST_SEASON_START_YEAR = 2025  # 2025-26; extend as seasons roll over

CSV_URL_TEMPLATE = "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"


def season_codes() -> list[str]:
    return [
        f"{y % 100:02d}{(y + 1) % 100:02d}"
        for y in range(FIRST_SEASON_START_YEAR, LAST_SEASON_START_YEAR + 1)
    ]


def season_label(code: str) -> str:
    start = int(code[:2])
    start += 2000 if start < 90 else 1900
    return f"{start}-{code[2:]}"
