"""Name normalisation for matching and search. Never used to *decide* a merge on its own."""
from __future__ import annotations

import re
import unicodedata

# Only generic legal/territorial suffixes are removed, one token at a time, so that "SSE Renewables Limited" and
# "SSE Renewables Ltd." always reduce to the same key. Words that distinguish trading entities ("renewables",
# "energy") are deliberately kept: "SSE plc" and "SSE Renewables" are different organisations.
_LEGAL = re.compile(r"\b(limited|ltd|plc|llp|lp|llc|inc|co|company|holdings?|group|uk|u\.k|gb|\(uk\))\b\.?")
# Words that carry no identity for a project name.
GENERIC_TOKENS = {
    "wind", "farm", "windfarm", "turbine", "turbines", "solar", "pv", "photovoltaic", "park", "array",
    "battery", "storage", "bess", "energy", "power", "project", "site", "station", "generating",
    "generation", "hydro", "scheme", "and", "the", "of", "plant", "facility", "phase", "extension",
    "repower", "repowering", "ltd", "limited", "renewable", "renewables", "onshore", "offshore",
    "mw", "grid", "reserve", "digestion", "anaerobic", "biogas", "biomass", "landfill", "gas",
    "development", "new", "land", "at",
}

# Tokens that distinguish sibling projects (Hornsea 1/2/3, Dogger Bank A/B/C, Vanguard East/West, Phase 2, Extension ...).
_NUMBER_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
                 "i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5"}
_COMPASS = {"north", "south", "east", "west", "northern", "southern", "eastern", "western"}
_VARIANT_WORDS = {"extension", "repower", "repowering", "phase", "stage"}


def variant_signature(s: str | None) -> frozenset[str]:
    """Identity-bearing variant markers in a project name. Two names with different signatures are different
    projects/phases until proven otherwise: 'Whitelee' vs 'Whitelee Extension', 'Hornsea 2' vs 'Hornsea 3'."""
    sig: set[str] = set()
    for t in norm_name(strip_parenthetical(s)).split():
        t = _NUMBER_WORDS.get(t, t)
        if t.isdigit() or t in _COMPASS or t in _VARIANT_WORDS or (len(t) == 1 and t in "abcd"):
            sig.add(t)
    # 'phase'/'stage' on their own carry no identity once a number/letter is present
    return frozenset(sig)


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def strip_parenthetical(s: str | None) -> str:
    """'Dogger Bank C (was Teesside A)' -> 'Dogger Bank C'. Parenthetical text is an alias/sub-area note, not identity."""
    return re.sub(r"\([^)]*\)", " ", s or "")


def norm_name(s: str | None) -> str:
    """lower-case, accent-free, '&'→'and', punctuation removed, whitespace collapsed."""
    if not s:
        return ""
    s = strip_accents(s).lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def core_name(s: str | None) -> str:
    """Identity-bearing tokens only (drops 'wind farm', 'BESS', 'phase 2' ...). May be empty."""
    toks = [_NUMBER_WORDS.get(t, t) for t in norm_name(strip_parenthetical(s)).split() if t not in GENERIC_TOKENS]
    return " ".join(toks)


def norm_org(s: str | None) -> str:
    """Key for grouping spelling variants of one organisation: case/punctuation/legal-suffix insensitive."""
    if not s:
        return ""
    s = norm_name(s)
    s = re.sub(_LEGAL, " ", s)
    return re.sub(r"\s+", " ", s).strip()


def phase_token(s: str | None) -> str | None:
    """Phase / extension marker found in a project name, e.g. 'phase 2', 'extension', 'a'."""
    n = norm_name(s)
    m = re.search(r"\b(phase|stage)\s*(\d+|[a-d]|i{1,3}|iv)\b", n)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    if re.search(r"\bextension\b", n):
        return "extension"
    if re.search(r"\brepower(ing)?\b", n):
        return "repower"
    return None
