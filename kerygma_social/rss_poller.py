"""RSS/Atom feed poller for detecting new content.

Polls a feed URL, tracks seen entries, and yields new items
for distribution. Handles both RSS 2.0 and Atom feeds using
stdlib xml.etree.
"""

from __future__ import annotations

import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ATOM_NS = "http://www.w3.org/2005/Atom"


@dataclass
class FeedEntry:
    """A single entry from an RSS/Atom feed."""
    entry_id: str
    title: str
    url: str
    summary: str = ""
    published: str = ""
    updated: str = ""


class RssPoller:
    """Polls RSS/Atom feeds and tracks seen entries."""

    def __init__(
        self,
        feed_url: str = "",
        seen_path: Path | None = None,
        fetch_func: Any | None = None,
    ) -> None:
        self._feed_url = feed_url
        self._seen_path = seen_path
        self._seen: set[str] = set()
        self._fetch = fetch_func  # Injectable for testing
        if seen_path and seen_path.exists():
            self._load_seen()

    def _load_seen(self) -> None:
        if not self._seen_path or not self._seen_path.exists():
            return
        try:
            data = json.loads(self._seen_path.read_text(encoding="utf-8"))
            self._seen = set(data.get("seen_ids", []))
        except (json.JSONDecodeError, TypeError):
            self._seen = set()

    def _save_seen(self) -> None:
        if not self._seen_path:
            return
        data = {"seen_ids": sorted(self._seen)}
        tmp = self._seen_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(str(tmp), str(self._seen_path))

    def _fetch_feed(self) -> str:
        """Fetch feed content from URL."""
        if self._fetch:
            return self._fetch(self._feed_url)
        req = urllib.request.Request(self._feed_url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")

    def parse_feed(self, xml_text: str) -> list[FeedEntry]:
        """Parse an RSS or Atom feed XML string into FeedEntry objects."""
        root = ET.fromstring(xml_text)
        entries: list[FeedEntry] = []

        # Try Atom first
        atom_entries = root.findall(f"{{{ATOM_NS}}}entry")
        if atom_entries:
            for entry in atom_entries:
                entry_id = self._text(entry, f"{{{ATOM_NS}}}id") or ""
                title = self._text(entry, f"{{{ATOM_NS}}}title") or ""
                link_el = entry.find(f"{{{ATOM_NS}}}link[@rel='alternate']")
                if link_el is None:
                    link_el = entry.find(f"{{{ATOM_NS}}}link")
                url = link_el.get("href", "") if link_el is not None else ""
                summary = self._text(entry, f"{{{ATOM_NS}}}summary") or ""
                published = self._text(entry, f"{{{ATOM_NS}}}published") or ""
                updated = self._text(entry, f"{{{ATOM_NS}}}updated") or ""
                entries.append(FeedEntry(
                    entry_id=entry_id, title=title, url=url,
                    summary=summary, published=published, updated=updated,
                ))
            return entries

        # Fall back to RSS 2.0
        for item in root.iter("item"):
            guid = self._text(item, "guid") or self._text(item, "link") or ""
            title = self._text(item, "title") or ""
            url = self._text(item, "link") or ""
            summary = self._text(item, "description") or ""
            published = self._text(item, "pubDate") or ""
            entries.append(FeedEntry(
                entry_id=guid, title=title, url=url,
                summary=summary, published=published,
            ))

        return entries

    def poll(self) -> list[FeedEntry]:
        """Fetch feed and return only new (unseen) entries."""
        xml_text = self._fetch_feed()
        all_entries = self.parse_feed(xml_text)
        new_entries = [e for e in all_entries if e.entry_id not in self._seen]

        for entry in new_entries:
            self._seen.add(entry.entry_id)

        self._save_seen()
        return new_entries

    def mark_seen(self, entry_id: str) -> None:
        self._seen.add(entry_id)
        self._save_seen()

    @property
    def seen_count(self) -> int:
        return len(self._seen)

    @staticmethod
    def _text(el: ET.Element, tag: str) -> str | None:
        child = el.find(tag)
        return child.text if child is not None else None
