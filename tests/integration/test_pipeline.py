import pytest
import time
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from ml.features.feature_engineering import RollingWindowAggregator
from ingestion.producers.log_producer import make_log, SERVICES


class TestProducerToFeatures:
    """Integration tests: producer output → feature engineering."""

    def test_producer_logs_flow_through_aggregator(self):
        agg = RollingWindowAggregator()
        # Generate 100 logs from producer and feed to aggregator
        for _ in range(100):
            import random
            service = random.choice(SERVICES)
            log = make_log(service)
            agg.add_log(log)

        features = agg.flush_all()
        assert len(features) > 0
        for f in features:
            assert f.total_logs > 0
            assert 0.0 <= f.error_rate <= 1.0
            assert f.avg_duration >= 0.0

    def test_error_rate_reflects_producer_error_logs(self):
        agg = RollingWindowAggregator()
        # Inject 50 ERROR logs and 50 INFO logs
        for i in range(50):
            agg.add_log({
                "service": "web-api", "level": "ERROR",
                "timestamp": i * 100, "duration_ms": 200
            })
        for i in range(50):
            agg.add_log({
                "service": "web-api", "level": "INFO",
                "timestamp": 5000 + i * 100, "duration_ms": 100
            })
        features = agg.flush_window("web-api")
        assert features is not None
        assert features.error_rate == pytest.approx(0.5)
        assert features.total_logs == 100
        assert features.error_count == 50

    def test_high_volume_window_processed_correctly(self):
        agg = RollingWindowAggregator()
        for i in range(1000):
            agg.add_log({
                "service": "payment-service",
                "level": "INFO",
                "timestamp": i * 10,
                "duration_ms": 100,
            })
        features = agg.flush_window("payment-service")
        assert features is not None
        assert features.total_logs == 1000

    def test_feature_vector_has_no_nan_values(self):
        import numpy as np
        from ml.features.feature_engineering import features_to_vector
        agg = RollingWindowAggregator()
        for i in range(20):
            agg.add_log(make_log("web-api"))
        features = agg.flush_window("web-api")
        vector = features_to_vector(features)
        assert not any(v != v for v in vector)  # NaN check

    def test_multiple_windows_build_history(self):
        agg = RollingWindowAggregator()
        # Window 1: 100 logs
        for i in range(100):
            agg.add_log(make_log("auth-service", timestamp=i*100))
        f1 = agg.flush_window("auth-service")
        assert f1.volume_delta == 0.0  # no history yet

        # Window 2: 200 logs
        for i in range(200):
            agg.add_log(make_log("auth-service", timestamp=10000 + i*100))
        f2 = agg.flush_window("auth-service")
        assert f2.volume_delta == pytest.approx(1.0)  # 100% increase


class TestMLPipeline:
    """Integration tests: features → model → prediction."""

    def test_model_files_exist(self):
        import os
        assert os.path.exists("ml/models/isolation_forest.pkl")
        assert os.path.exists("ml/models/scaler.pkl")
        assert os.path.exists("ml/models/threshold.json")

    def test_model_loads_successfully(self):
        import pickle
        with open("ml/models/isolation_forest.pkl", "rb") as f:
            model = pickle.load(f)
        assert model is not None
        assert hasattr(model, "score_samples")

    def test_threshold_is_valid_float(self):
        import json
        with open("ml/models/threshold.json") as f:
            data = json.load(f)
        assert "threshold" in data
        assert isinstance(data["threshold"], float)
        assert -1.0 < data["threshold"] < 0.0

    def test_normal_features_score_above_threshold(self):
        import pickle
        import json
        import numpy as np
        from ml.models.predict import load_threshold

        with open("ml/models/isolation_forest.pkl", "rb") as f:
            model = pickle.load(f)
        with open("ml/models/scaler.pkl", "rb") as f:
            scaler = pickle.load(f)
        threshold = load_threshold()

        # Normal feature vector
        normal = np.array([[0.02, 0.05, 150.0, 400.0, 0.05, 1.1, 100.0, 2.0]])
        scaled = scaler.transform(normal)
        score  = model.score_samples(scaled)[0]
        assert score > threshold

    def test_anomalous_features_score_below_threshold(self):
        import pickle
        import numpy as np
        from ml.models.predict import load_threshold

        with open("ml/models/isolation_forest.pkl", "rb") as f:
            model = pickle.load(f)
        with open("ml/models/scaler.pkl", "rb") as f:
            scaler = pickle.load(f)
        threshold = load_threshold()

        # Clear anomaly: 80% error rate, 15x spike
        anomalous = np.array([[0.80, 0.10, 150.0, 400.0, 0.0, 15.0, 100.0, 80.0]])
        scaled    = scaler.transform(anomalous)
        score     = model.score_samples(scaled)[0]
        assert score < threshold