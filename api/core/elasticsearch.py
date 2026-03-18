from elasticsearch import AsyncElasticsearch

_client: AsyncElasticsearch | None = None


def get_es_client() -> AsyncElasticsearch:
    global _client
    if _client is None:
        _client = AsyncElasticsearch("http://localhost:9200")
    return _client


async def close_es_client():
    global _client
    if _client is not None:
        await _client.close()
        _client = None