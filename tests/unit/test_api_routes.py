import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self, client):
        response = client.get("/health")
        assert response.json() == {"status": "ok"}


class TestSearchEndpoint:

    def test_search_invalid_page_returns_422(self, client):
        response = client.get("/api/logs/search?page=0")
        assert response.status_code == 422

    def test_search_invalid_page_size_too_large(self, client):
        response = client.get("/api/logs/search?page_size=1000")
        assert response.status_code == 422

    def test_search_valid_params_accepted(self):
        # Test that query building logic accepts valid params
        # without needing a real ES connection
        from api.routes.logs import build_es_query
        query = build_es_query("error", "web-api", "ERROR", None, None)
        assert query is not None
        assert "bool" in query

    def test_search_level_filter_structure(self):
        from api.routes.logs import build_es_query
        query = build_es_query(None, None, "ERROR", None, None)
        assert "ERROR" in str(query)

    def test_search_service_filter_structure(self):
        from api.routes.logs import build_es_query
        query = build_es_query(None, "web-api", None, None, None)
        assert "web-api" in str(query)
        
class TestQueryBuilding:

    def test_build_es_query_no_filters(self):
        from api.routes.logs import build_es_query
        query = build_es_query(None, None, None, None, None)
        assert "bool" in query
        assert "match_all" in str(query)

    def test_build_es_query_with_text_search(self):
        from api.routes.logs import build_es_query
        query = build_es_query("timeout", None, None, None, None)
        assert "match" in str(query)
        assert "timeout" in str(query)

    def test_build_es_query_with_service_filter(self):
        from api.routes.logs import build_es_query
        query = build_es_query(None, "web-api", None, None, None)
        assert "web-api" in str(query)
        assert "term" in str(query)

    def test_build_es_query_with_level_filter(self):
        from api.routes.logs import build_es_query
        query = build_es_query(None, None, "error", None, None)
        assert "ERROR" in str(query)

    def test_build_es_query_level_uppercased(self):
        from api.routes.logs import build_es_query
        query = build_es_query(None, None, "warn", None, None)
        assert "WARN" in str(query)
        assert "warn" not in str(query)

    def test_build_es_query_with_time_range(self):
        from api.routes.logs import build_es_query
        query = build_es_query(None, None, None, 1000, 2000)
        assert "range" in str(query)
        assert "1000" in str(query)
        assert "2000" in str(query)

    def test_build_es_query_combined_filters(self):
        from api.routes.logs import build_es_query
        query = build_es_query("timeout", "web-api", "ERROR", 1000, 2000)
        q_str = str(query)
        assert "timeout"  in q_str
        assert "web-api"  in q_str
        assert "ERROR"    in q_str
        assert "range"    in q_str