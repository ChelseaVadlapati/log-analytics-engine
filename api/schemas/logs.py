from pydantic import BaseModel
from typing import Optional


class LogSearchParams(BaseModel):
    query:    Optional[str] = None
    service:  Optional[str] = None
    level:    Optional[str] = None
    from_ts:  Optional[int] = None   # epoch ms
    to_ts:    Optional[int] = None   # epoch ms
    page:     int = 1
    page_size: int = 50


class LogEvent(BaseModel):
    event_id:    str
    timestamp:   int
    service:     str
    level:       str
    message:     str
    trace_id:    Optional[str] = None
    duration_ms: Optional[int] = None
    host:        str
    is_error:    Optional[bool] = None
    ingested_at: Optional[int] = None


class SearchResponse(BaseModel):
    total:   int
    page:    int
    pages:   int
    results: list[LogEvent]