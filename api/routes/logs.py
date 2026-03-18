from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from elasticsearch import AsyncElasticsearch

from api.core.elasticsearch import get_es_client
from api.schemas.logs import SearchResponse, LogEvent

router = APIRouter(prefix="/api/logs", tags=["logs"])


def get_index_name() -> str:
    month = datetime.utcnow().strftime("%Y-%m")
    return f"applogs-{month}"


def build_es_query(
    query:    Optional[str],
    service:  Optional[str],
    level:    Optional[str],
    from_ts:  Optional[int],
    to_ts:    Optional[int],
) -> dict:
    must_clauses = []
    filter_clauses = []

    # Full-text search on message field
    if query:
        must_clauses.append({
            "match": {"message": {"query": query, "operator": "and"}}
        })

    # Exact filters
    if service:
        filter_clauses.append({"term": {"service": service}})
    if level:
        filter_clauses.append({"term": {"level": level.upper()}})

    # Time range filter
    if from_ts or to_ts:
        range_filter: dict = {"range": {"timestamp": {}}}
        if from_ts:
            range_filter["range"]["timestamp"]["gte"] = from_ts
        if to_ts:
            range_filter["range"]["timestamp"]["lte"] = to_ts
        filter_clauses.append(range_filter)

    return {
        "bool": {
            "must":   must_clauses   or [{"match_all": {}}],
            "filter": filter_clauses,
        }
    }


@router.get("/search", response_model=SearchResponse)
async def search_logs(
    query:     Optional[str] = Query(None, description="Full-text search on message"),
    service:   Optional[str] = Query(None, description="Filter by service name"),
    level:     Optional[str] = Query(None, description="Filter by log level"),
    from_ts:   Optional[int] = Query(None, description="Start time (epoch ms)"),
    to_ts:     Optional[int] = Query(None, description="End time (epoch ms)"),
    page:      int           = Query(1,    ge=1),
    page_size: int           = Query(50,   ge=1, le=500),
    es: AsyncElasticsearch   = Depends(get_es_client),
):
    es_query = build_es_query(query, service, level, from_ts, to_ts)
    from_offset = (page - 1) * page_size

    response = await es.search(
        index=get_index_name(),
        query=es_query,
        sort=[{"timestamp": {"order": "desc"}}],
        from_=from_offset,
        size=page_size,
    )

    hits  = response["hits"]["hits"]
    total = response["hits"]["total"]["value"]
    pages = max(1, -(-total // page_size))  # ceiling division

    results = [LogEvent(**hit["_source"]) for hit in hits]

    return SearchResponse(
        total=total,
        page=page,
        pages=pages,
        results=results,
    )


@router.get("/count")
async def count_logs(
    service: Optional[str]       = Query(None),
    level:   Optional[str]       = Query(None),
    es:      AsyncElasticsearch  = Depends(get_es_client),
):
    es_query = build_es_query(None, service, level, None, None)
    response = await es.count(index=get_index_name(), query=es_query)
    return {"count": response["count"]}


@router.get("/services")
async def list_services(es: AsyncElasticsearch = Depends(get_es_client)):
    response = await es.search(
        index=get_index_name(),
        size=0,
        aggs={"services": {"terms": {"field": "service", "size": 50}}},
    )
    buckets = response["aggregations"]["services"]["buckets"]
    return {"services": [b["key"] for b in buckets]}