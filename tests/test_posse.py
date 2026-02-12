"""Tests for the posse module."""
from src.posse import PosseDistributor, Platform, SyndicationStatus

def test_create_post():
    dist = PosseDistributor()
    post = dist.create_post("P001", "Launch Day", "We are live", "https://example.com/launch", [Platform.MASTODON])
    assert post.post_id == "P001"
    assert Platform.MASTODON in post.platforms

def test_syndicate_creates_records():
    dist = PosseDistributor()
    dist.create_post("P001", "Test", "Body", "https://example.com", [Platform.MASTODON, Platform.DISCORD])
    records = dist.syndicate("P001")
    assert len(records) == 2
    assert all(r.status == SyndicationStatus.PUBLISHED for r in records)

def test_syndication_record_urls():
    dist = PosseDistributor()
    dist.create_post("P001", "Test", "Body", "https://example.com", [Platform.MASTODON])
    records = dist.syndicate("P001")
    assert records[0].external_url is not None
    assert "mastodon" in records[0].external_url
