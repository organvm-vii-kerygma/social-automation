"""Tests for the RSS poller module."""

from pathlib import Path

from kerygma_social.rss_poller import RssPoller, FeedEntry

FIXTURES = Path(__file__).parent / "fixtures"


class TestRssPoller:
    def test_parse_atom_feed(self):
        xml = FIXTURES.joinpath("sample_feed.xml").read_text()
        poller = RssPoller()
        entries = poller.parse_feed(xml)
        assert len(entries) == 2
        assert entries[0].title == "Orchestrating the Eight Organs"
        assert "01-orchestrate" in entries[0].url

    def test_parse_rss_feed(self):
        rss = """<?xml version="1.0"?>
        <rss version="2.0"><channel><title>Test</title>
        <item><title>Item 1</title><link>https://example.com/1</link>
        <guid>id-1</guid><description>Desc</description></item>
        </channel></rss>"""
        poller = RssPoller()
        entries = poller.parse_feed(rss)
        assert len(entries) == 1
        assert entries[0].title == "Item 1"

    def test_poll_returns_new_entries(self):
        xml = FIXTURES.joinpath("sample_feed.xml").read_text()
        poller = RssPoller(
            feed_url="unused",
            fetch_func=lambda _: xml,
        )
        new = poller.poll()
        assert len(new) == 2

    def test_poll_skips_seen_entries(self):
        xml = FIXTURES.joinpath("sample_feed.xml").read_text()
        poller = RssPoller(feed_url="unused", fetch_func=lambda _: xml)

        first = poller.poll()
        assert len(first) == 2

        second = poller.poll()
        assert len(second) == 0

    def test_seen_persistence(self, tmp_path):
        xml = FIXTURES.joinpath("sample_feed.xml").read_text()
        seen_path = tmp_path / "seen.json"

        poller1 = RssPoller(
            feed_url="unused", seen_path=seen_path, fetch_func=lambda _: xml,
        )
        poller1.poll()
        assert seen_path.exists()
        assert poller1.seen_count == 2

        poller2 = RssPoller(
            feed_url="unused", seen_path=seen_path, fetch_func=lambda _: xml,
        )
        new = poller2.poll()
        assert len(new) == 0

    def test_mark_seen(self):
        poller = RssPoller()
        poller.mark_seen("test-id")
        assert poller.seen_count == 1

    def test_feed_entry_dataclass(self):
        entry = FeedEntry(
            entry_id="id1", title="Test", url="https://example.com",
            summary="A test entry", published="2026-01-01",
        )
        assert entry.entry_id == "id1"
