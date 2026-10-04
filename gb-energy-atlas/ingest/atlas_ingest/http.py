"""Polite HTTP: robots.txt aware, per-host rate limited, retried, content-hashed, cached on disk."""
from __future__ import annotations

import hashlib
import re
import time
import urllib.robotparser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

from . import config


class SourceUnavailable(Exception):
    """Host unreachable / blocked / gateway-denied."""


class SourceRestricted(Exception):
    """Reachable but gated (403/401, API key required, empty export)."""


class ManualReviewRequired(Exception):
    """No machine-readable route that is legitimate to automate."""


def robots_overridden(url: str) -> bool:
    """True when this URL is fetched only because the operator explicitly overrode robots.txt for its host."""
    p = urlparse(url)
    if not config.RESPECT_ROBOTS or p.netloc.lower() not in config.ROBOTS_OVERRIDE_HOSTS:
        return False
    base = f"{p.scheme}://{p.netloc}"
    rp = _robots.get(base)
    return rp is not None and not rp.can_fetch(config.USER_AGENT, url)


@dataclass
class Fetched:
    path: Path
    url: str
    sha256: str
    size: int
    status: int
    content_type: str | None
    etag: str | None
    last_modified: str | None


_last_hit: dict[str, float] = {}
_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
_session = requests.Session()
_session.headers["User-Agent"] = config.USER_AGENT


def _throttle(host: str) -> None:
    wait = config.MIN_REQUEST_INTERVAL - (time.monotonic() - _last_hit.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.monotonic()


def _robots_msg(url: str) -> str:
    host = urlparse(url).netloc
    return (f"robots.txt on {host} disallows automated access to {url}. Not fetched. Options: download the file via the "
            f"publisher's portal and run `atlas-ingest ingest <source> --file <path> --source-url <url>`, or – after reviewing the "
            f"licence/terms – explicitly set ATLAS_ROBOTS_OVERRIDE={host}.")


def robots_allows(url: str) -> bool:
    if not config.RESPECT_ROBOTS:
        return True
    p = urlparse(url)
    if p.netloc.lower() in config.ROBOTS_OVERRIDE_HOSTS:
        return True  # explicit operator override; recorded on the snapshot
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            _throttle(p.netloc)
            r = _session.get(f"{base}/robots.txt", timeout=30)
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
                _robots[base] = rp
            else:
                _robots[base] = None  # no robots.txt → nothing disallowed
        except requests.RequestException:
            _robots[base] = None
    rp = _robots[base]
    return True if rp is None else rp.can_fetch(config.USER_AGENT, url)


def _safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)[:120]


def get(url: str, *, source_key: str, label: str = "", params: dict | None = None,
        headers: dict | None = None, suffix: str = "", retries: int = 3) -> Fetched:
    """Download `url` to data/raw/<source_key>/ and return its hash. Raises the typed exceptions above."""
    if not robots_allows(url):
        raise ManualReviewRequired(_robots_msg(url))
    host = urlparse(url).netloc
    last_exc: Exception | None = None
    for attempt in range(retries):
        _throttle(host)
        try:
            r = _session.get(url, params=params, headers=headers, timeout=config.REQUEST_TIMEOUT, stream=True)
        except requests.RequestException as exc:  # connection reset / proxy 502 on CONNECT etc.
            last_exc = exc
            time.sleep(2 ** attempt)
            continue
        if r.status_code in (401, 403):
            raise SourceRestricted(f"HTTP {r.status_code} from {host}")
        if r.status_code in (502, 503, 504) and attempt < retries - 1:
            time.sleep(2 ** attempt)
            continue
        if r.status_code >= 400:
            raise SourceUnavailable(f"HTTP {r.status_code} from {url}")
        out_dir = config.DATA_DIR / source_key
        out_dir.mkdir(parents=True, exist_ok=True)
        tmp = out_dir / f".dl-{int(time.time()*1000)}.part"
        h = hashlib.sha256()
        size = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                h.update(chunk)
                size += len(chunk)
        digest = h.hexdigest()
        ext = suffix or Path(urlparse(url).path).suffix or ".bin"
        final = out_dir / f"{_safe_name(label or 'file')}_{digest[:12]}{ext}"
        tmp.replace(final)
        return Fetched(final, url, digest, size, r.status_code, r.headers.get("content-type"),
                       r.headers.get("etag"), r.headers.get("last-modified"))
    raise SourceUnavailable(f"{host}: {type(last_exc).__name__ if last_exc else 'unreachable'}: {last_exc}")


def get_text(url: str, *, retries: int = 3, headers: dict | None = None, params: dict | None = None) -> tuple[str, int]:
    """Small text/JSON fetch (landing pages, catalogue APIs) with the same politeness rules."""
    if not robots_allows(url):
        raise ManualReviewRequired(_robots_msg(url))
    host = urlparse(url).netloc
    last_exc: Exception | None = None
    for attempt in range(retries):
        _throttle(host)
        try:
            r = _session.get(url, timeout=60, headers=headers, params=params)
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(2 ** attempt)
            continue
        if r.status_code in (401, 403):
            raise SourceRestricted(f"HTTP {r.status_code} from {host}")
        if r.status_code in (502, 503, 504) and attempt < retries - 1:
            time.sleep(2 ** attempt)
            continue
        if r.status_code >= 400:
            raise SourceUnavailable(f"HTTP {r.status_code} from {url}")
        return r.text, r.status_code
    raise SourceUnavailable(f"{host}: {last_exc}")
