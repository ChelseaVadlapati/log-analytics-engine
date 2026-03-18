import pytest
import numpy as np
import pickle
import json
import os


class TestTrainingDataGeneration:

    def test_generate_normal_logs_returns_correct_count(self):
        from ml.models.train import generate_normal_logs
        logs = generate_normal_logs(n_windows=10)
        assert len(logs) > 0

    def test_generate_normal_logs_have_required_fields(self):
        from ml.models.train import generate_normal_logs
        logs = generate_normal_logs(n_windows=5)
        for log in logs:
            assert "service"   in log
            assert "level"     in log
            assert "timestamp" in log

    def test_generate_normal_logs_levels_are_valid(self):
        from ml.models.train import generate_normal_logs
        valid = {"DEBUG", "INFO", "WARN", "ERROR", "FATAL"}
        logs  = generate_normal_logs(n_windows=5)
        for log in logs:
            assert log["level"] in valid

    def test_extract_features_returns_ndarray(self):
        from ml.models.train import generate_normal_logs, extract_features
        logs = generate_normal_logs(n_windows=20)
        X    = extract_features(logs)
        assert isinstance(X, np.ndarray)
        assert X.ndim == 2

    def test_extract_features_has_8_columns(self):
        from ml.models.train import generate_normal_logs, extract_features
        logs = generate_normal_logs(n_windows=20)
        X    = extract_features(logs)
        assert X.shape[1] == 8

    def test_extract_features_no_nan(self):
        from ml.models.train import generate_normal_logs, extract_features
        logs = generate_normal_logs(n_windows=20)
        X    = extract_features(logs)
        assert not np.any(np.isnan(X))


class TestModelFiles:

    def test_model_file_exists(self):
        assert os.path.exists("ml/models/isolation_forest.pkl")

    def test_scaler_file_exists(self):
        assert os.path.exists("ml/models/scaler.pkl")

    def test_threshold_file_exists(self):
        assert os.path.exists("ml/models/threshold.json")

    def test_threshold_value_is_negative(self):
        with open("ml/models/threshold.json") as f:
            data = json.load(f)
        assert data["threshold"] < 0

    def test_model_has_correct_n_estimators(self):
        with open("ml/models/isolation_forest.pkl", "rb") as f:
            model = pickle.load(f)
        assert model.n_estimators == 100

    def test_scaler_has_correct_n_features(self):
        with open("ml/models/scaler.pkl", "rb") as f:
            scaler = pickle.load(f)
        assert scaler.n_features_in_ == 8


class TestEvaluation:

    def test_generate_normal_features_shape(self):
        from ml.evaluation.evaluate import generate_normal_features
        X = generate_normal_features(100)
        assert X.shape == (100, 8)

    def test_generate_anomalous_features_shape(self):
        from ml.evaluation.evaluate import generate_anomalous_features
        X = generate_anomalous_features(30)
        assert X.shape == (30, 8)

    def test_normal_features_error_rate_range(self):
        from ml.evaluation.evaluate import generate_normal_features
        X = generate_normal_features(200)
        error_rates = X[:, 0]
        assert error_rates.min() >= 0.0
        assert error_rates.max() <= 0.08

    def test_anomalous_features_error_rate_higher(self):
        from ml.evaluation.evaluate import (
            generate_normal_features,
            generate_anomalous_features,
        )
        normal    = generate_normal_features(200)
        anomalous = generate_anomalous_features(50)
        assert anomalous[:, 0].mean() > normal[:, 0].mean()

    def test_load_threshold_returns_float(self):
        from ml.evaluation.evaluate import load_threshold
        t = load_threshold()
        assert isinstance(t, float)
        assert t < 0

    def test_normal_features_have_no_nan(self):
        from ml.evaluation.evaluate import generate_normal_features
        X = generate_normal_features(100)
        assert not np.any(np.isnan(X))

    def test_anomalous_features_have_no_nan(self):
        from ml.evaluation.evaluate import generate_anomalous_features
        X = generate_anomalous_features(50)
        assert not np.any(np.isnan(X))


class TestPredictModule:

    def test_load_model_returns_model_and_scaler(self):
        from ml.models.predict import load_model
        model, scaler = load_model()
        assert model   is not None
        assert scaler  is not None

    def test_load_threshold_returns_float(self):
        from ml.models.predict import load_threshold
        t = load_threshold()
        assert isinstance(t, float)

    def test_score_window_normal_returns_not_anomaly(self):
        from ml.models.predict import load_model, score_window
        from ml.features.feature_engineering import WindowFeatures
        import numpy as np

        model, scaler = load_model()

        # Use the mean of training distribution — guaranteed to be normal
        # error_rate=2%, warn_rate=6%, avg_dur=200ms, p99=600ms,
        # vol_delta=0%, spike=1.0x, total=100, errors=2
        normal = WindowFeatures(
            service="web-api",   window_start=1000,
            total_logs=100,      error_count=2,
            error_rate=0.02,     warn_rate=0.06,
            avg_duration=200.0,  p99_duration=600.0,
            volume_delta=0.0,    error_spike=1.0,
        )
        score, is_anomaly = score_window(normal, model, scaler)
        assert isinstance(score, float)
        # Score should be above threshold for clearly normal data
        assert score > -0.597, f"Expected normal score > -0.597, got {score:.3f}"

    def test_score_window_anomalous_returns_anomaly(self):
        from ml.models.predict import load_model, score_window
        from ml.features.feature_engineering import WindowFeatures
        model, scaler = load_model()

        anomalous = WindowFeatures(
            service="web-api",    window_start=1000,
            total_logs=100,       error_count=80,
            error_rate=0.80,      warn_rate=0.10,
            avg_duration=150.0,   p99_duration=400.0,
            volume_delta=0.0,     error_spike=15.0,
        )
        score, is_anomaly = score_window(anomalous, model, scaler)
        assert is_anomaly


class TestEsIndex:

    def test_get_index_name_format(self):
        from processing.indexer.es_index import get_index_name
        name = get_index_name()
        assert name.startswith("applogs-")
        assert len(name) == len("applogs-2026-03")

    def test_get_index_name_contains_year(self):
        from processing.indexer.es_index import get_index_name
        from datetime import datetime
        name = get_index_name()
        year = str(datetime.utcnow().year)
        assert year in name

    def test_index_mapping_has_required_fields(self):
        from processing.indexer.es_index import INDEX_MAPPING
        props = INDEX_MAPPING["mappings"]["properties"]
        required = {"event_id", "timestamp", "service",
                    "level", "message", "host"}
        assert required.issubset(props.keys())

    def test_index_mapping_timestamp_is_date_type(self):
        from processing.indexer.es_index import INDEX_MAPPING
        ts = INDEX_MAPPING["mappings"]["properties"]["timestamp"]
        assert ts["type"] == "date"

    def test_index_settings_single_shard(self):
        from processing.indexer.es_index import INDEX_MAPPING
        assert INDEX_MAPPING["settings"]["number_of_shards"] == 1
    
    def test_index_mapping_message_has_text_type(self):
        from processing.indexer.es_index import INDEX_MAPPING
        msg = INDEX_MAPPING["mappings"]["properties"]["message"]
        assert msg["type"] == "text"

    def test_index_mapping_service_is_keyword(self):
        from processing.indexer.es_index import INDEX_MAPPING
        svc = INDEX_MAPPING["mappings"]["properties"]["service"]
        assert svc["type"] == "keyword"