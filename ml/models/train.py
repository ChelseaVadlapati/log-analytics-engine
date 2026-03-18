import json
import os
import pickle
import random
import time

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ml.features.feature_engineering import (
    RollingWindowAggregator,
    features_to_vector,
    FEATURE_NAMES,
)

SERVICES      = ["web-api", "auth-service", "payment-service"]
MODEL_PATH    = "ml/models/isolation_forest.pkl"
SCALER_PATH   = "ml/models/scaler.pkl"


def generate_normal_logs(n_windows: int = 500) -> list[dict]:
    """
    Generate synthetic normal-operation log windows for training.
    Simulates 7 days of healthy service behaviour with natural variation.
    """
    logs = []
    base_ts = int(time.time() * 1000) - (7 * 24 * 3600 * 1000)

    for window_idx in range(n_windows):
        service  = random.choice(SERVICES)
        # Natural variation: busy periods, quiet periods
        n_logs   = random.randint(40, 200)
        ts_start = base_ts + window_idx * 60_000

        # Vary error rates naturally (0-8% is normal)
        error_weight = random.uniform(0, 0.08)
        warn_weight  = random.uniform(0, 0.12)
        info_weight  = 1 - error_weight - warn_weight

        for i in range(n_logs):
            level = random.choices(
                ["DEBUG", "INFO", "WARN", "ERROR"],
                weights=[0.1, max(info_weight, 0.5), warn_weight, error_weight]
            )[0]
            # Natural duration variation: fast and slow requests
            duration = random.choices(
                [
                    random.randint(5, 100),    # fast
                    random.randint(100, 500),   # normal
                    random.randint(500, 1500),  # slow but ok
                ],
                weights=[0.6, 0.3, 0.1]
            )[0]
            logs.append({
                "service":     service,
                "level":       level,
                "timestamp":   ts_start + i * 500,
                "duration_ms": duration if random.random() > 0.3 else None,
            })
    return logs


def extract_features(logs: list[dict]) -> np.ndarray:
    """Run logs through the aggregator and return feature matrix."""
    agg = RollingWindowAggregator(window_seconds=60)

    # Group logs by 60-second windows
    windows_by_service: dict[str, list[dict]] = {}
    for log in logs:
        s = log["service"]
        if s not in windows_by_service:
            windows_by_service[s] = []
        windows_by_service[s].append(log)

    feature_vectors = []
    for service, service_logs in windows_by_service.items():
        # Sort by timestamp and process in 60s chunks
        service_logs.sort(key=lambda x: x["timestamp"])
        chunk_start = service_logs[0]["timestamp"]

        chunk: list[dict] = []
        for log in service_logs:
            if log["timestamp"] - chunk_start > 60_000:
                for l in chunk:
                    agg.add_log(l)
                features = agg.flush_window(service)
                if features:
                    feature_vectors.append(features_to_vector(features))
                chunk = [log]
                chunk_start = log["timestamp"]
            else:
                chunk.append(log)

        if chunk:
            for l in chunk:
                agg.add_log(l)
            features = agg.flush_window(service)
            if features:
                feature_vectors.append(features_to_vector(features))

    return np.array(feature_vectors)


def train():
    print("Generating training data...")
    logs = generate_normal_logs(n_windows=500)
    print(f"Generated {len(logs)} synthetic log events")

    print("Extracting features...")
    X = extract_features(logs)
    print(f"Feature matrix shape: {X.shape}")
    print(f"Features: {FEATURE_NAMES}")

    print("Fitting scaler...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print("Training Isolation Forest...")
    model = IsolationForest(
        n_estimators=100,
        contamination=0.02,   # expect 2% anomalous windows
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_scaled)

    # Save model and scaler
    os.makedirs("ml/models", exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    print(f"Model saved to {MODEL_PATH}")
    print(f"Scaler saved to {SCALER_PATH}")

    # Quick sanity check — normal data should mostly score > threshold
    scores = model.score_samples(X_scaled)
    threshold = float(np.percentile(scores, 2))
    print(f"\nTraining score stats:")
    print(f"  Min:  {scores.min():.3f}")
    print(f"  Max:  {scores.max():.3f}")
    print(f"  Mean: {scores.mean():.3f}")
    print(f" Suggested threshold (p2): {threshold:.3f}")
    print(f"  Anomalies at p2 threshold: "
          f"{(scores < threshold).sum()} / {len(scores)}")
    
    # Save threshold alongside model
    import json
    with open("ml/models/threshold.json", "w") as f:
        json.dump({"threshold": threshold}, f)
    print(f"\nThreshold saved to ml/models/threshold.json")
    print("\nTraining complete.")


if __name__ == "__main__":
    train()