import asyncio
import json
import pickle
import time

import httpx
import numpy as np

from ml.features.feature_engineering import (
    RollingWindowAggregator,
    features_to_vector,
    WindowFeatures,
)

MODEL_PATH  = "ml/models/isolation_forest.pkl"
SCALER_PATH = "ml/models/scaler.pkl"
ES_URL      = "http://localhost:9200"
THRESHOLD   = -0.1
WINDOW_SECS = 60


def load_model():
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)
    return model, scaler


def score_window(
    features: WindowFeatures,
    model,
    scaler,
) -> tuple[float, bool]:
    """Returns (anomaly_score, is_anomaly)."""
    vector   = np.array(features_to_vector(features)).reshape(1, -1)
    scaled   = scaler.transform(vector)
    score    = float(model.score_samples(scaled)[0])
    return score, score < THRESHOLD


async def send_slack_alert(
    webhook_url: str,
    features: WindowFeatures,
    score: float,
):
    if not webhook_url:
        print(f"[ALERT] Anomaly in {features.service} "
              f"(score={score:.3f}, error_rate={features.error_rate:.1%})")
        return

    message = {
        "text": (
            f":rotating_light: *Anomaly detected* in `{features.service}`\n"
            f"• Score: `{score:.3f}` (threshold: {THRESHOLD})\n"
            f"• Error rate: `{features.error_rate:.1%}`\n"
            f"• Volume delta: `{features.volume_delta:+.1%}`\n"
            f"• Error spike ratio: `{features.error_spike:.2f}x`\n"
            f"• Window: `{features.total_logs}` logs"
        )
    }
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json=message, timeout=5.0)


async def fetch_recent_logs(
    es_client: httpx.AsyncClient,
    since_ms: int,
    until_ms: int,
) -> list[dict]:
    response = await es_client.post(
        f"{ES_URL}/applogs-*/_search",
        json={
            "query": {
                "range": {
                    "ingested_at": {"gt": since_ms, "lte": until_ms}
                }
            },
            "size": 10000,
            "sort": [{"ingested_at": {"order": "asc"}}],
        },
        timeout=10.0,
    )
    data = response.json()
    return [hit["_source"] for hit in data.get("hits", {}).get("hits", [])]

def load_threshold() -> float:
    import json
    try:
        with open("ml/models/threshold.json") as f:
            return json.load(f)["threshold"]
    except FileNotFoundError:
        return -0.5  # safe fallback

async def run_pipeline(slack_webhook: str = ""):
    print("Loading model...")
    model, scaler = load_model()
    print(f"Model loaded. Anomaly threshold: {THRESHOLD}")
    print(f"Pipeline running — scoring every {WINDOW_SECS}s per service\n")

    agg      = RollingWindowAggregator(window_seconds=WINDOW_SECS)
    services = ["web-api", "auth-service", "payment-service"]
    last_ms  = int(time.time() * 1000) - WINDOW_SECS * 1000

    async with httpx.AsyncClient() as es:
        while True:
            await asyncio.sleep(WINDOW_SECS)
            now_ms = int(time.time() * 1000)

            print(f"[{time.strftime('%H:%M:%S')}] Fetching logs "
                  f"from last {WINDOW_SECS}s...")

            logs = await fetch_recent_logs(es, last_ms, now_ms)
            last_ms = now_ms

            if not logs:
                print("  No logs in window — skipping")
                continue

            print(f"  Processing {len(logs)} logs...")
            for log in logs:
                agg.add_log(log)

            for service in services:
                features = agg.flush_window(service)
                if not features:
                    continue

                score, is_anomaly = score_window(features, model, scaler)
                status = "ANOMALY" if is_anomaly else "normal"
                print(
                    f"  {service:20s} | score={score:+.3f} | "
                    f"errors={features.error_rate:.1%} | "
                    f"vol_delta={features.volume_delta:+.1%} | "
                    f"{status}"
                )

                if is_anomaly:
                    await send_slack_alert(slack_webhook, features, score)


if __name__ == "__main__":
    asyncio.run(run_pipeline())