from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

# Mock services before importing app
import app.services.qdrant_client as qdrant
import app.services.llm_client as llm

qdrant.qdrant_service.initialize = AsyncMock()
qdrant.qdrant_service.close = AsyncMock()
qdrant.qdrant_service.health_check = AsyncMock(return_value=True)

llm.llm_client.initialize = AsyncMock()
llm.llm_client.close = AsyncMock()
llm.llm_client.health_check = AsyncMock(return_value=True)

from app.main import app  # noqa: E402
from app.config import settings  # noqa: E402

client = TestClient(app)

def test_cors_allowed_origin():
    """Test that an allowed origin receives correct CORS headers."""
    origin = "http://localhost:3000"
    assert origin in settings.backend_cors_origins

    response = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"

def test_cors_disallowed_origin():
    """Test that a disallowed origin does not receive CORS headers."""
    origin = "http://malicious.com"
    assert origin not in settings.backend_cors_origins

    response = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        }
    )
    # FastAPI's CORSMiddleware returns 400 for disallowed origins in preflight if Origin header is present
    # Or it might just not include the headers.
    assert response.headers.get("access-control-allow-origin") is None

def test_cors_get_request_allowed():
    """Test a GET request from an allowed origin."""
    origin = "http://localhost:3000"
    response = client.get(
        "/health",
        headers={"Origin": origin}
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin

def test_cors_get_request_disallowed():
    """Test a GET request from a disallowed origin."""
    origin = "http://malicious.com"
    response = client.get(
        "/health",
        headers={"Origin": origin}
    )
    assert response.status_code == 200 # Request still succeeds, but without CORS headers
    assert response.headers.get("access-control-allow-origin") is None
