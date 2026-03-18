import pytest
from ingestion.producers.log_producer import make_log, SERVICES, LEVELS, MESSAGES


class TestMakeLog:

    def test_returns_all_required_fields(self):
        log = make_log("web-api")
        required = {"event_id", "timestamp", "service",
                    "level", "message", "host"}
        assert required.issubset(log.keys())

    def test_service_field_matches_input(self):
        for service in SERVICES:
            log = make_log(service)
            assert log["service"] == service

    def test_level_is_valid(self):
        valid_levels = {"DEBUG", "INFO", "WARN", "ERROR", "FATAL"}
        for _ in range(50):
            log = make_log("web-api")
            assert log["level"] in valid_levels

    def test_event_id_is_uuid_format(self):
        import re
        log = make_log("web-api")
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, log["event_id"])

    def test_timestamp_is_recent_epoch_ms(self):
        import time
        log = make_log("web-api")
        now_ms = int(time.time() * 1000)
        assert log["timestamp"] <= now_ms
        assert log["timestamp"] > now_ms - 5000

    def test_host_contains_service_name(self):
        log = make_log("auth-service")
        assert "auth-service" in log["host"]

    def test_duration_ms_is_none_or_positive_int(self):
        results = [make_log("web-api")["duration_ms"] for _ in range(100)]
        for d in results:
            if d is not None:
                assert isinstance(d, int)
                assert d > 0

    def test_trace_id_is_none_or_uuid(self):
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        results = [make_log("web-api")["trace_id"] for _ in range(100)]
        for t in results:
            if t is not None:
                assert re.match(uuid_pattern, t)

    def test_all_services_have_messages_defined(self):
        for service in SERVICES:
            assert service in MESSAGES
            assert len(MESSAGES[service]) > 0

    def test_message_is_non_empty_string(self):
        for service in SERVICES:
            log = make_log(service)
            assert isinstance(log["message"], str)
            assert len(log["message"]) > 0