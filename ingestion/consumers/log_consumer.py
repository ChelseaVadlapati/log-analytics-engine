import asyncio
import json
import time
from datetime import datetime

from aiokafka import AIOKafkaConsumer
from elasticsearch import AsyncElasticsearch, helpers

KAFKA_BOOTSTRAP = "localhost:9092"
ES_URL          = "http://localhost:9200"
TOPICS          = ["logs.web-api", "logs.auth-service", "logs.payment-service"]
CONSUMER_GROUP  = "log-analytics-consumers"
BATCH_SIZE      = 500
FLUSH_INTERVAL  = 2.0  # seconds — flush even if batch isn't full


def get_index_name() -> str:
    month = datetime.utcnow().strftime("%Y-%m")
    return f"applogs-{month}"


def enrich_log(log: dict) -> dict:
    """Add derived fields to the log event."""
    # Normalise level to uppercase
    log["level"] = log.get("level", "INFO").upper()

    # Tag ERROR and FATAL logs
    log["is_error"] = log["level"] in ("ERROR", "FATAL")

    # Add ingest timestamp so we can measure pipeline latency
    log["ingested_at"] = int(time.time() * 1000)

    return log


def make_es_action(log: dict, index: str) -> dict:
    """Convert a log dict into an Elasticsearch bulk action."""
    return {
        "_index": index,
        "_id":    log["event_id"],   # idempotent — re-indexing same event is safe
        "_source": log,
    }


async def consume():
    es = AsyncElasticsearch(ES_URL)
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=CONSUMER_GROUP,
        value_deserializer=lambda v: json.loads(v.decode()),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    await consumer.start()
    print(f"Consumer started — listening on: {', '.join(TOPICS)}")
    print(f"Batch size: {BATCH_SIZE} | Flush interval: {FLUSH_INTERVAL}s\n")

    batch       = []
    last_flush  = time.monotonic()
    total_indexed = 0

    try:
        async for message in consumer:
            log = enrich_log(message.value)
            batch.append(make_es_action(log, get_index_name()))

            time_since_flush = time.monotonic() - last_flush
            should_flush = (
                len(batch) >= BATCH_SIZE or
                time_since_flush >= FLUSH_INTERVAL
            )

            if should_flush and batch:
                success, failed = await helpers.async_bulk(
                    es,
                    batch,
                    raise_on_error=False,
                )
                total_indexed += success
                last_flush = time.monotonic()

                print(
                    f"[{time.strftime('%H:%M:%S')}] "
                    f"Indexed {success} logs "
                    f"({total_indexed} total)"
                    + (f" | {failed} failed" if failed else "")
                )
                batch = []

    except KeyboardInterrupt:
        print(f"\nStopping. Total indexed: {total_indexed}")
    finally:
        # Flush remaining batch before shutdown
        if batch:
            success, _ = await helpers.async_bulk(es, batch, raise_on_error=False)
            total_indexed += success
            print(f"Final flush: {success} logs. Total: {total_indexed}")
        await consumer.stop()
        await es.close()


if __name__ == "__main__":
    asyncio.run(consume())