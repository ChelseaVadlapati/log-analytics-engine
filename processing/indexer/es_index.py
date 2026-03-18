import asyncio
from datetime import datetime

from elasticsearch import AsyncElasticsearch, NotFoundError

ES_URL = "http://localhost:9200"

INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "event_id":    {"type": "keyword"},
            "timestamp":   {"type": "date", "format": "epoch_millis"},
            "service":     {"type": "keyword"},
            "level":       {"type": "keyword"},
            "message":     {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword", "ignore_above": 512}
                }
            },
            "trace_id":    {"type": "keyword"},
            "duration_ms": {"type": "integer"},
            "host":        {"type": "keyword"},
            "is_error":    {"type": "boolean"},
            "ingested_at": {"type": "date", "format": "epoch_millis"},
        }
    },
    "settings": {
        "number_of_shards":   1,
        "number_of_replicas": 0,
        "refresh_interval":   "1s"
    }
}


def get_index_name() -> str:
    month = datetime.utcnow().strftime("%Y-%m")
    return f"applogs-{month}"


async def create_index_if_not_exists():
    es = AsyncElasticsearch(ES_URL)
    try:
        index = get_index_name()
        try:
            await es.indices.get(index=index)
            print(f"Index already exists: {index}")
        except NotFoundError:
            await es.indices.create(
                index=index,
                mappings=INDEX_MAPPING["mappings"],
                settings=INDEX_MAPPING["settings"],
            )
            print(f"Created index: {index}")
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(create_index_if_not_exists())