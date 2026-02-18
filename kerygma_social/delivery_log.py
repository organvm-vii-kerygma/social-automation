"""Persistent delivery log for tracking dispatch records.

Records every syndication attempt to a JSON file, enabling
deduplication, auditing, and retry of failed deliveries.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class DeliveryRecord:
    """A single delivery attempt."""
    record_id: str
    post_id: str
    platform: str
    status: str  # "success", "failure", "skipped"
    timestamp: str = ""
    external_url: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class DeliveryLog:
    """JSON file-backed delivery log."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        self._records: list[DeliveryRecord] = []
        if path and path.exists():
            self._load()

    def _load(self) -> None:
        if not self._path or not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._records = [
                DeliveryRecord(**rec) for rec in data.get("records", [])
            ]
        except (json.JSONDecodeError, TypeError):
            self._records = []

    def _save(self) -> None:
        if not self._path:
            return
        data = {"records": [asdict(r) for r in self._records]}
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(str(tmp), str(self._path))

    def append(self, record: DeliveryRecord) -> None:
        self._records.append(record)
        self._save()

    def get_by_post(self, post_id: str) -> list[DeliveryRecord]:
        return [r for r in self._records if r.post_id == post_id]

    def get_by_platform(self, platform: str) -> list[DeliveryRecord]:
        return [r for r in self._records if r.platform == platform]

    def get_failures(self) -> list[DeliveryRecord]:
        return [r for r in self._records if r.status == "failure"]

    def has_been_delivered(self, post_id: str, platform: str) -> bool:
        return any(
            r.post_id == post_id and r.platform == platform and r.status == "success"
            for r in self._records
        )

    @property
    def total_records(self) -> int:
        return len(self._records)

    @property
    def all_records(self) -> list[DeliveryRecord]:
        return list(self._records)
