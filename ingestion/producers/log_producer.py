import asyncio
import json
import random
import time
import uuid

from aiokafka import AIOKafkaProducer

SERVICES = ["web-api", "auth-service", "payment-service"]

LEVELS = ["DEBUG", "INFO", "INFO", "INFO", "WARN", "ERROR"]

MESSAGES = {
    "web-api": [
        "GET /api/users 200 {ms}ms",
        "POST /api/orders 201 {ms}ms",
        "GET /api/products 200 {ms}ms",
        "GET /api/health 200 {ms}ms",
        "Connection timeout after {ms}ms",
        "Unhandled exception in request handler",
        "Rate limit exceeded for IP 10.0.0.{n}",
    ],
    "auth-service": [
        "Token validated for user_{id}",
        "Login success user_{id} in {ms}ms",
        "Invalid token attempt from 192.168.1.{n}",
        "JWT verification failed: signature mismatch",
        "Rate limit exceeded for IP 10.0.0.{n}",
        "Password reset requested for user_{id}",
        "Session expired for user_{id}",
    ],
    "payment-service": [
        "Payment processed ${amount} txn_{id}",
        "Stripe webhook received order_{id}",
        "Database query completed in {ms}ms",
        "Payment gateway timeout after {ms}ms",
        "Refund initiated for order_{id}",
        "Card declined for user_{id}",
        "Fraud check passed for txn_{id}",
    ],
}


def make_log(service: str, timestamp: int = None) -> dict:
    level = random.choice(LEVELS)
    ms = random.randint(5, 2000)
    template = random.choice(MESSAGES[service])
    message = template.format(
        ms=ms,
        id=random.randint(1000, 9999),
        n=random.randint(1, 255),
        amount=round(random.uniform(10, 500), 2),
    )
    return {
        "event_id":    str(uuid.uuid4()),
        "timestamp":   timestamp if timestamp is not None else int(time.time() * 1000),
        "service":     service,
        "level":       level,
        "message":     message,
        "trace_id":    str(uuid.uuid4()) if random.random() > 0.3 else None,
        "duration_ms": ms if random.random() > 0.4 else None,
        "host":        f"pod-{service}-{random.randint(1, 3)}",
    }


async def produce(rate_per_sec: int = 100):
    producer = AIOKafkaProducer(
        bootstrap_servers="localhost:9092",
        value_serializer=lambda v: json.dumps(v).encode(),
        key_serializer=lambda k: k.encode() if k else b"no-key",
    )

    await producer.start()
    print(f"Producer started — sending {rate_per_sec} logs/sec across {len(SERVICES)} services")
    print("Topics: " + ", ".join(f"logs.{s}" for s in SERVICES))
    print("Press Ctrl+C to stop\n")

    sent_total = 0

    try:
        while True:
            batch_start = time.monotonic()

            for _ in range(rate_per_sec):
                service = random.choice(SERVICES)
                log = make_log(service)
                await producer.send(
                    topic=f"logs.{service}",
                    value=log,
                    key=log["trace_id"] or log["event_id"],
                )
                sent_total += 1

            # flush to ensure delivery
            await producer.flush()

            elapsed = time.monotonic() - batch_start
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)

            print(f"[{time.strftime('%H:%M:%S')}] Sent {rate_per_sec} logs "
                  f"({sent_total} total) — {elapsed:.2f}s per batch")

    except KeyboardInterrupt:
        print(f"\nStopping. Total logs sent: {sent_total}")
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(produce(rate_per_sec=100))