import json
import pickle
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix


MODEL_PATH  = "ml/models/isolation_forest.pkl"
SCALER_PATH = "ml/models/scaler.pkl"


def load_threshold() -> float:
    try:
        with open("ml/models/threshold.json") as f:
            return json.load(f)["threshold"]
    except FileNotFoundError:
        return -0.55


def generate_normal_features(n: int = 450) -> np.ndarray:
    """
    Generate feature vectors representing healthy service windows.
    Features: [error_rate, warn_rate, avg_duration, p99_duration,
               volume_delta, error_spike, total_logs, error_count]
    """
    rng = np.random.default_rng(42)
    return np.column_stack([
        rng.uniform(0.00, 0.08, n),     # error_rate: 0-8%
        rng.uniform(0.00, 0.12, n),     # warn_rate:  0-12%
        rng.uniform(50,  400,   n),     # avg_duration ms
        rng.uniform(200, 1200,  n),     # p99_duration ms
        rng.uniform(-0.3, 0.3,  n),     # volume_delta: ±30%
        rng.uniform(0.5,  2.0,  n),     # error_spike ratio
        rng.uniform(40,  200,   n),     # total_logs
        rng.uniform(0,   12,    n),     # error_count
    ])


def generate_anomalous_features(n: int = 50) -> np.ndarray:
    """
    Generate feature vectors representing anomalous windows.
    Each type represents a distinct fault pattern.
    """
    rng   = np.random.default_rng(99)
    third = n // 3

    # Fault 1: error spike — high error rate, high spike ratio
    error_spike = np.column_stack([
        rng.uniform(0.35, 0.80, third),   # error_rate: 35-80%
        rng.uniform(0.10, 0.30, third),   # warn_rate
        rng.uniform(50,   400,  third),   # avg_duration normal
        rng.uniform(200,  1200, third),   # p99_duration normal
        rng.uniform(-0.2, 0.2,  third),   # volume_delta normal
        rng.uniform(5.0,  15.0, third),   # error_spike: 5-15x
        rng.uniform(40,   200,  third),   # total_logs normal
        rng.uniform(30,   80,   third),   # error_count high
    ])

    # Fault 2: volume spike — massive log volume, unusual traffic
    volume_spike = np.column_stack([
        rng.uniform(0.05, 0.15, third),   # error_rate slightly elevated
        rng.uniform(0.05, 0.20, third),   # warn_rate
        rng.uniform(50,   400,  third),   # avg_duration
        rng.uniform(200,  1200, third),   # p99_duration
        rng.uniform(3.0,  8.0,  third),   # volume_delta: 300-800% spike
        rng.uniform(1.0,  3.0,  third),   # error_spike
        rng.uniform(500,  1000, third),   # total_logs: massive
        rng.uniform(20,   60,   third),   # error_count elevated
    ])

    # Fault 3: slow requests — very high latency
    remaining = n - 2 * third
    slow_requests = np.column_stack([
        rng.uniform(0.02, 0.10, remaining),   # error_rate normal
        rng.uniform(0.10, 0.30, remaining),   # warn_rate elevated
        rng.uniform(3000, 8000, remaining),   # avg_duration: very slow
        rng.uniform(6000, 15000, remaining),  # p99_duration: very slow
        rng.uniform(-0.2, 0.2,  remaining),   # volume_delta normal
        rng.uniform(1.0,  2.0,  remaining),   # error_spike normal
        rng.uniform(40,   200,  remaining),   # total_logs normal
        rng.uniform(2,    12,   remaining),   # error_count normal
    ])

    return np.vstack([error_spike, volume_spike, slow_requests])


def evaluate():
    print("Loading model and scaler...")
    with open(MODEL_PATH,  "rb") as f:
        model = pickle.load(f)
    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)

    threshold = load_threshold()
    print(f"Using threshold: {threshold:.3f}")

    print("Generating golden dataset...")
    normal_X    = generate_normal_features(450)
    anomalous_X = generate_anomalous_features(50)

    print(f"Normal windows:    {len(normal_X)}")
    print(f"Anomalous windows: {len(anomalous_X)}")

    X      = np.vstack([normal_X, anomalous_X])
    y_true = np.array([0] * len(normal_X) + [1] * len(anomalous_X))

    X_scaled = scaler.transform(X)
    scores   = model.score_samples(X_scaled)
    y_pred   = (scores < threshold).astype(int)

    print("\n" + "=" * 50)
    print("EVALUATION RESULTS")
    print("=" * 50)
    print(classification_report(
        y_true, y_pred,
        target_names=["normal", "anomaly"],
        zero_division=0,
    ))

    cm = confusion_matrix(y_true, y_pred)
    print("Confusion matrix:")
    print(f"  True negatives  (normal  → normal):  {cm[0][0]}")
    print(f"  False positives (normal  → anomaly): {cm[0][1]}")
    print(f"  False negatives (anomaly → normal):  {cm[1][0]}")
    print(f"  True positives  (anomaly → anomaly): {cm[1][1]}")

    precision = cm[1][1] / (cm[1][1] + cm[0][1]) if (cm[1][1] + cm[0][1]) > 0 else 0
    recall    = cm[1][1] / (cm[1][1] + cm[1][0]) if (cm[1][1] + cm[1][0]) > 0 else 0
    print(f"\nPrecision: {precision:.2f}")
    print(f"Recall:    {recall:.2f}")

    if recall >= 0.85 and precision >= 0.50:
        print("\nBoth targets met: recall >= 0.85 and precision >= 0.50")
    elif recall >= 0.85:
        print(f"\nRecall target met. Precision {precision:.2f} below 0.50 target.")
    else:
        print(f"\nBelow recall target: {recall:.2f} (need 0.85)")


if __name__ == "__main__":
    evaluate()