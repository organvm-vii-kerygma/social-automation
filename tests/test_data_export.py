"""Tests for kerygma_social.data_export module."""
import json
from pathlib import Path

import pytest

from kerygma_social.data_export import (
    build_delivery_log_schema,
    build_posse_manifest,
    export_all,
)


@pytest.fixture
def tmp_output(tmp_path):
    return tmp_path / "data"


def test_build_delivery_log_schema():
    result = build_delivery_log_schema()
    assert result["record_format"] == "DeliveryRecord"
    assert len(result["fields"]) > 0
    assert len(result["platforms"]) > 0
    assert "sample_record" in result


def test_delivery_log_schema_has_all_platforms():
    result = build_delivery_log_schema()
    assert "mastodon" in result["platforms"]
    assert "bluesky" in result["platforms"]
    assert "discord" in result["platforms"]
    assert "ghost" in result["platforms"]


def test_delivery_log_schema_sample_record():
    result = build_delivery_log_schema()
    sample = result["sample_record"]
    assert "record_id" in sample
    assert "post_id" in sample
    assert "platform" in sample
    assert "status" in sample


def test_build_posse_manifest():
    result = build_posse_manifest()
    assert result["pattern"] == "POSSE (Publish Own Site, Syndicate Everywhere)"
    assert len(result["platforms"]) > 0
    assert len(result["resilience_stack"]) == 4
    assert len(result["config_fields"]) > 0


def test_posse_manifest_platforms_have_env_vars():
    result = build_posse_manifest()
    mastodon = next(p for p in result["platforms"] if p["platform"] == "mastodon")
    assert len(mastodon["env_vars"]) > 0
    assert "KERYGMA_MASTODON_INSTANCE_URL" in mastodon["env_vars"]


def test_export_all_creates_two_files(tmp_output):
    paths = export_all(tmp_output)
    assert len(paths) == 2
    names = {p.name for p in paths}
    assert "delivery-log.json" in names
    assert "posse-manifest.json" in names


def test_export_all_valid_json(tmp_output):
    paths = export_all(tmp_output)
    for p in paths:
        data = json.loads(p.read_text())
        assert data["organ"] == "VII"
        assert data["organ_name"] == "Kerygma"
        assert data["repo"] == "social-automation"
        assert "generated_at" in data
