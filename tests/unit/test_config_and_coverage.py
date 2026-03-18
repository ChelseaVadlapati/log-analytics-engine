import pytest
import numpy as np
import json
import os


class TestConfig:

    def test_settings_loads_with_defaults(self):
        from api.core.config import get_settings
        s = get_settings()
        assert s.kafka_bootstrap_servers == "localhost:9092"
        assert s.elasticsearch_url == "http://localhost:9200"
        assert s.api_port == 8000
        assert s.log_level == "INFO"

    def test_settings_kafka_consumer_group(self):
        from api.core.config import get_settings
        s = get_settings()
        assert s.kafka_consumer_group == "log-analytics-consumers"

    def test_settings_postgres_url(self):
        from api.core.config import get_settings
        s = get_settings()
        assert "logdb" in s.postgres_url

    def test_settings_redis_url(self):
        from api.core.config import get_settings
        s = get_settings()
        assert s.redis_url.startswith("redis://")

    def test_settings_ml_defaults(self):
        from api.core.config import get_settings
        s = get_settings()
        assert s.anomaly_threshold == -0.1
        assert s.feature_window_seconds == 60

    def test_settings_slack_webhook_default_empty(self):
        from api.core.config import get_settings
        s = get_settings()
        assert s.slack_webhook_url == ""

    def test_get_settings_returns_same_instance(self):
        from api.core.config import get_settings
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2  # lru_cache returns same instance

    def test_settings_schema_registry_url(self):
        from api.core.config import get_settings
        s = get_settings()
        assert "8081" in s.kafka_schema_registry_url

    def test_settings_elasticsearch_index_prefix(self):
        from api.core.config import get_settings
        s = get_settings()
        assert s.elasticsearch_index_prefix == "logs"


class TestProducerAsyncFunctions:

    def test_services_list_has_three_entries(self):
        from ingestion.producers.log_producer import SERVICES
        assert len(SERVICES) == 3

    def test_levels_list_contains_info(self):
        from ingestion.producers.log_producer import LEVELS
        assert "INFO" in LEVELS

    def test_messages_dict_has_all_services(self):
        from ingestion.producers.log_producer import MESSAGES, SERVICES
        for s in SERVICES:
            assert s in MESSAGES
            assert len(MESSAGES[s]) >= 5

    def test_make_log_all_services_produce_valid_logs(self):
        from ingestion.producers.log_producer import make_log, SERVICES
        for service in SERVICES:
            for _ in range(10):
                log = make_log(service)
                assert log["service"] == service
                assert isinstance(log["message"], str)
                assert len(log["message"]) > 0

    def test_make_log_with_explicit_timestamp(self):
        from ingestion.producers.log_producer import make_log
        log = make_log("web-api", timestamp=999999)
        assert log["timestamp"] == 999999

    def test_make_log_without_timestamp_uses_current(self):
        import time
        from ingestion.producers.log_producer import make_log
        before = int(time.time() * 1000)
        log    = make_log("web-api")
        after  = int(time.time() * 1000)
        assert before <= log["timestamp"] <= after


class TestEvaluateFunction:

    def test_evaluate_runs_without_error(self):
        """Run the full evaluate() function and verify it completes."""
        import io
        import sys
        from ml.evaluation.evaluate import evaluate
        captured = io.StringIO()
        sys.stdout = captured
        try:
            evaluate()
        finally:
            sys.stdout = sys.__stdout__
        output = captured.getvalue()
        assert "EVALUATION RESULTS" in output
        assert "Precision:" in output
        assert "Recall:" in output

    def test_evaluate_output_contains_confusion_matrix(self):
        import io
        import sys
        from ml.evaluation.evaluate import evaluate
        captured = io.StringIO()
        sys.stdout = captured
        try:
            evaluate()
        finally:
            sys.stdout = sys.__stdout__
        output = captured.getvalue()
        assert "Confusion matrix" in output
        assert "True negatives"   in output
        assert "True positives"   in output


class TestTrainFunction:

    def test_generate_normal_logs_n_windows_respected(self):
        from ml.models.train import generate_normal_logs
        logs = generate_normal_logs(n_windows=10)
        # Each window generates between 40-200 logs
        assert len(logs) >= 10 * 40
        assert len(logs) <= 10 * 200

    def test_generate_normal_logs_timestamps_increase(self):
        from ml.models.train import generate_normal_logs
        logs = generate_normal_logs(n_windows=5)
        # Sort by timestamp — first log should have earliest timestamp
        timestamps = [l["timestamp"] for l in logs]
        assert min(timestamps) < max(timestamps)

    def test_extract_features_returns_correct_columns(self):
        from ml.models.train import generate_normal_logs, extract_features
        logs = generate_normal_logs(n_windows=15)
        X    = extract_features(logs)
        assert X.shape[1] == 8

    def test_extract_features_values_are_finite(self):
        from ml.models.train import generate_normal_logs, extract_features
        logs = generate_normal_logs(n_windows=15)
        X    = extract_features(logs)
        assert np.all(np.isfinite(X))

    def test_model_contamination_parameter(self):
        import pickle
        with open("ml/models/isolation_forest.pkl", "rb") as f:
            model = pickle.load(f)
        assert model.contamination == 0.02

    def test_model_random_state_is_set(self):
        import pickle
        with open("ml/models/isolation_forest.pkl", "rb") as f:
            model = pickle.load(f)
        assert model.random_state == 42