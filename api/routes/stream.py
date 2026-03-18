import asyncio
import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from elasticsearch import AsyncElasticsearch

from api.core.elasticsearch import get_es_client

router = APIRouter(prefix="/api/logs", tags=["stream"])


def get_index_name() -> str:
    from datetime import datetime
    month = datetime.utcnow().strftime("%Y-%m")
    return f"applogs-{month}"


@router.websocket("/tail")
async def log_tail(websocket: WebSocket):
    await websocket.accept()
    es = get_es_client()

    # Start from logs ingested in the last 5 seconds
    last_seen_ts = int(time.time() * 1000) - 5000

    try:
        while True:
            now_ts = int(time.time() * 1000)

            response = await es.search(
                index=get_index_name(),
                query={
                    "range": {
                        "ingested_at": {
                            "gt":  last_seen_ts,
                            "lte": now_ts,
                        }
                    }
                },
                sort=[{"ingested_at": {"order": "asc"}}],
                size=100,
            )

            hits = response["hits"]["hits"]

            if hits:
                last_seen_ts = hits[-1]["_source"]["ingested_at"]
                for hit in hits:
                    await websocket.send_text(
                        json.dumps(hit["_source"])
                    )

            # Poll every second
            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        pass