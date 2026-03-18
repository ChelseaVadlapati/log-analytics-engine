import pytest
from ml.features.feature_engineering import (
    RollingWindowAggregator,
    features_to_vector,
    WindowFeatures,
    FEATURE_NAMES,
)


def make_log(service="web-api", level="INFO", duration_ms=100, timestamp=1000):
    return {
        "service":     service,
        "level":       level,
        "timestamp":   timestamp,
        "duration_ms": duration_ms,
    }


class TestRollingWindowAggregator:

    def test_add_single_log_increments_count(self):
        agg = RollingWindowAggregator()
        agg.add_log(make_log())
        assert agg._counts["web-api"] == 1

    def test_error_logs_increment_error_count(self):
        agg = RollingWindowAggregator()
        agg.add_log(make_log(level="ERROR"))
        agg.add_log(make_log(level="FATAL"))
        agg.add_log(make_log(level="INFO"))
        assert agg._errors["web-api"] == 2

    def test_warn_logs_increment_warn_count(self):
        agg = RollingWindowAggregator()
        agg.add_log(make_log(level="WARN"))
        agg.add_log(make_log(level="INFO"))
        assert agg._warns["web-api"] == 1

    def test_flush_returns_window_features(self):
        agg = RollingWindowAggregator()
        for i in range(10):
            agg.add_log(make_log(level="INFO", duration_ms=100, timestamp=i*1000))
        features = agg.flush_window("web-api")
        assert features is not None
        assert isinstance(features, WindowFeatures)
        assert features.service == "web-api"
        assert features.total_logs == 10

    def test_flush_resets_counters(self):
        agg = RollingWindowAggregator()
        agg.add_log(make_log())
        agg.flush_window("web-api")
        assert agg._counts["web-api"] == 0
        assert agg._errors["web-api"] == 0

    def test_error_rate_calculation(self):
        agg = RollingWindowAggregator()
        agg.add_log(make_log(level="ERROR"))
        agg.add_log(make_log(level="INFO"))
        agg.add_log(make_log(level="INFO"))
        agg.add_log(make_log(level="INFO"))
        features = agg.flush_window("web-api")
        assert features.error_rate == pytest.approx(0.25)

    def test_flush_empty_window_returns_none(self):
        agg = RollingWindowAggregator()
        result = agg.flush_window("web-api")
        assert result is None

    def test_multiple_services_tracked_independently(self):
        agg = RollingWindowAggregator()
        agg.add_log(make_log(service="web-api",       level="ERROR"))
        agg.add_log(make_log(service="auth-service",  level="INFO"))
        agg.add_log(make_log(service="auth-service",  level="INFO"))
        assert agg._counts["web-api"]      == 1
        assert agg._counts["auth-service"] == 2
        assert agg._errors["web-api"]      == 1
        assert agg._errors["auth-service"] == 0

    def test_flush_all_returns_all_services(self):
        agg = RollingWindowAggregator()
        agg.add_log(make_log(service="web-api"))
        agg.add_log(make_log(service="auth-service"))
        agg.add_log(make_log(service="payment-service"))
        results = agg.flush_all()
        services = {f.service for f in results}
        assert services == {"web-api", "auth-service", "payment-service"}

    def test_p99_duration_calculation(self):
        agg = RollingWindowAggregator()
        # Add 100 logs with duration 1-100ms
        for i in range(1, 101):
            agg.add_log(make_log(duration_ms=i, timestamp=i*100))
        features = agg.flush_window("web-api")
        # p99 of 1-100 should be close to 100
        assert features.p99_duration >= 98

    def test_null_duration_ignored(self):
        agg = RollingWindowAggregator()
        agg.add_log({
            "service": "web-api", "level": "INFO",
            "timestamp": 1000, "duration_ms": None
        })
        features = agg.flush_window("web-api")
        assert features is not None
        assert features.avg_duration == 0.0

    def test_volume_delta_after_two_windows(self):
        agg = RollingWindowAggregator()
        # First window: 10 logs
        for i in range(10):
            agg.add_log(make_log(timestamp=i*100))
        agg.flush_window("web-api")
        # Second window: 20 logs (100% increase)
        for i in range(20):
            agg.add_log(make_log(timestamp=10000 + i*100))
        features = agg.flush_window("web-api")
        assert features.volume_delta == pytest.approx(1.0)  # 100% increase


class TestFeaturesToVector:

    def test_returns_correct_length(self):
        f = WindowFeatures(
            service="web-api", window_start=1000,
            total_logs=100, error_count=5,
            error_rate=0.05, warn_rate=0.10,
            avg_duration=200.0, p99_duration=800.0,
            volume_delta=0.1, error_spike=1.2,
        )
        vector = features_to_vector(f)
        assert len(vector) == len(FEATURE_NAMES)

    def test_vector_matches_feature_order(self):
        f = WindowFeatures(
            service="web-api", window_start=1000,
            total_logs=100, error_count=10,
            error_rate=0.10, warn_rate=0.05,
            avg_duration=300.0, p99_duration=900.0,
            volume_delta=0.2, error_spike=1.5,
        )
        vector = features_to_vector(f)
        assert vector[0] == pytest.approx(0.10)   # error_rate
        assert vector[1] == pytest.approx(0.05)   # warn_rate
        assert vector[2] == pytest.approx(300.0)  # avg_duration
        assert vector[6] == pytest.approx(100.0)  # total_logs