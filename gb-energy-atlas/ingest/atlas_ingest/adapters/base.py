"""Adapter contract. One adapter per source; adapters never write to the database themselves."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterator

from ..model import NormRecord, Reject


@dataclass
class Resource:
    """One downloadable file/endpoint of a source."""
    url: str
    label: str = ""                       # distinguishes several files under one source_key (e.g. a CfD round)
    publication_date: date | None = None
    suffix: str = ""
    headers: dict[str, str] | None = None
    licence_text: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class Adapter:
    source_key: str = ""

    def discover(self) -> list[Resource]:
        """Return the current resources. Raise SourceUnavailable / SourceRestricted / ManualReviewRequired honestly."""
        raise NotImplementedError

    def parse(self, path: Path, resource: Resource) -> Iterator[tuple[int, str | None, dict[str, Any]]]:
        """Yield (row_number, record_key, raw_payload) with original strings untouched."""
        raise NotImplementedError

    def validate_structure(self, payload: dict[str, Any]) -> str | None:
        """Return a reason to quarantine a structurally broken row, else None."""
        return None

    def normalise(self, payload: dict[str, Any], row_number: int, resource: Resource) -> NormRecord | Reject:
        raise NotImplementedError

    def registry_update(self, resource: Resource) -> dict[str, Any]:
        """Optional extra registry fields discovered at run time (e.g. licence from dataset metadata)."""
        return {}
