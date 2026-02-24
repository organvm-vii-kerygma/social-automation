"""Tests for the delivery log module."""


from kerygma_social.delivery_log import DeliveryLog, DeliveryRecord


class TestDeliveryLog:
    def test_append_and_count(self):
        log = DeliveryLog()
        log.append(DeliveryRecord(
            record_id="r1", post_id="p1", platform="mastodon", status="success",
        ))
        assert log.total_records == 1

    def test_get_by_post(self):
        log = DeliveryLog()
        log.append(DeliveryRecord(record_id="r1", post_id="p1", platform="mastodon", status="success"))
        log.append(DeliveryRecord(record_id="r2", post_id="p2", platform="discord", status="success"))
        assert len(log.get_by_post("p1")) == 1

    def test_get_by_platform(self):
        log = DeliveryLog()
        log.append(DeliveryRecord(record_id="r1", post_id="p1", platform="mastodon", status="success"))
        log.append(DeliveryRecord(record_id="r2", post_id="p2", platform="mastodon", status="failure"))
        assert len(log.get_by_platform("mastodon")) == 2

    def test_get_failures(self):
        log = DeliveryLog()
        log.append(DeliveryRecord(record_id="r1", post_id="p1", platform="mastodon", status="success"))
        log.append(DeliveryRecord(record_id="r2", post_id="p2", platform="discord", status="failure", error="timeout"))
        failures = log.get_failures()
        assert len(failures) == 1
        assert failures[0].error == "timeout"

    def test_has_been_delivered(self):
        log = DeliveryLog()
        log.append(DeliveryRecord(record_id="r1", post_id="p1", platform="mastodon", status="success"))
        assert log.has_been_delivered("p1", "mastodon") is True
        assert log.has_been_delivered("p1", "discord") is False

    def test_persistence(self, tmp_path):
        path = tmp_path / "log.json"
        log1 = DeliveryLog(path)
        log1.append(DeliveryRecord(record_id="r1", post_id="p1", platform="mastodon", status="success"))
        assert path.exists()

        log2 = DeliveryLog(path)
        assert log2.total_records == 1
        assert log2.get_by_post("p1")[0].platform == "mastodon"

    def test_auto_timestamp(self):
        rec = DeliveryRecord(record_id="r1", post_id="p1", platform="mastodon", status="success")
        assert len(rec.timestamp) > 0

    def test_max_records_trims_oldest(self, tmp_path):
        path = tmp_path / "log.json"
        log = DeliveryLog(path, max_records=3)
        for i in range(5):
            log.append(DeliveryRecord(
                record_id=f"r{i}", post_id=f"p{i}", platform="mastodon", status="success",
            ))
        assert log.total_records == 3
        # Oldest records (r0, r1) should have been trimmed
        assert log.get_by_post("p0") == []
        assert log.get_by_post("p1") == []
        assert len(log.get_by_post("p4")) == 1
