"""Honest probe adapters for sources we investigated but cannot ingest. Each run re-tests the route and records the outcome."""
from __future__ import annotations

from ..http import ManualReviewRequired, get_text
from .base import Adapter, Resource


class ProbeAdapter(Adapter):
    def __init__(self, source_key: str, url: str, reason: str) -> None:
        self.source_key, self.url, self.reason = source_key, url, reason

    def discover(self) -> list[Resource]:
        get_text(self.url)  # raises SourceRestricted / SourceUnavailable / ManualReviewRequired honestly
        raise ManualReviewRequired(f"{self.url} is reachable but no machine-readable bulk route is implemented: {self.reason}")
