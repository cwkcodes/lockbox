"""Organisation normalisation: many spellings -> one canonical record. Never infers parent/subsidiary links from names."""
from __future__ import annotations

from collections import Counter, defaultdict

import re

from .textnorm import norm_org


def split_orgs(raw: str | None) -> list[str]:
    """REPD lists joint operators in one string ('A / B'). Split on '/' and ';' (not on '&' or 'and', which occur inside names)."""
    if not raw:
        return []
    parts = [p.strip() for p in re.split(r"\s*[/;]\s*", raw)]
    out: list[str] = []
    for p in parts:
        if len(norm_org(p)) >= 2 and p not in out:
            out.append(p)
    return out



def _display_score(raw: str, count: int) -> tuple:
    """Prefer mixed-case spellings over SHOUTING, then the most frequent, then the shortest."""
    upper = raw.isupper()
    return (not upper, count, -len(raw))


class OrgIndex:
    def __init__(self) -> None:
        self._spellings: dict[str, Counter] = defaultdict(Counter)

    def observe(self, raw: str | None) -> str | None:
        key = norm_org(raw)
        if not key:
            return None
        self._spellings[key][raw.strip()] += 1  # type: ignore[union-attr]
        return key

    def canonical(self, key: str) -> tuple[str, list[str]]:
        sp = self._spellings[key]
        best = max(sp, key=lambda r: _display_score(r, sp[r]))
        return best, sorted(r for r in sp if r != best)

    def keys(self):
        return self._spellings.keys()
