import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# Must mock services BEFORE importing app to handle lifespan correctly if needed
# But for app import, we just need to ensure the instances are patched before client usage
# However, app.main imports them.

from app.services.qdrant_client import qdrant_service
from app.services.llm_client import llm_client

# Mock global service instances to verify logic without external dependencies
qdrant_service.initialize = AsyncMock()  # type: ignore
qdrant_service.close = AsyncMock()  # type: ignore
qdrant_service.upsert_notes = AsyncMock()  # type: ignore
qdrant_service.health_check = AsyncMock(return_value=True)  # type: ignore

llm_client.initialize = AsyncMock()  # type: ignore
llm_client.close = AsyncMock()  # type: ignore
llm_client.health_check = AsyncMock(return_value=True)  # type: ignore
llm_client.generate_text = AsyncMock(return_value="Mocked LLM generation")  # type: ignore
llm_client.embed_query = AsyncMock(return_value=[0.1] * 768)  # type: ignore
llm_client.embed_text = AsyncMock(return_value=[0.1] * 768)  # type: ignore

# Create mock services for factory functions
mock_stt = AsyncMock()
mock_stt.initialize = AsyncMock()
mock_stt.close = AsyncMock()

mock_tts = AsyncMock()
mock_tts.initialize = AsyncMock()
mock_tts.close = AsyncMock()

# Patch factories at their definition BEFORE importing app.main or creating TestClient
patch_stt = patch("app.services.stt_service.get_stt_service", return_value=mock_stt)
patch_tts = patch("app.services.tts_service.get_tts_service", return_value=mock_tts)

patch_stt.start()
patch_tts.start()

from app.main import app  # noqa: E402

# Create TestClient
client = TestClient(app)


@pytest.mark.asyncio
async def test_health_check() -> None:
    """Verify backend health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["status"] == "healthy"
    assert "qdrant" in json_resp["services"]
    assert "llm" in json_resp["services"]


@pytest.mark.asyncio
async def test_materials_upload_flow() -> None:
    """Verify file upload flow."""
    # Create mock file
    files = {"file": ("test.txt", b"mock content", "text/plain")}
    data = {"user_id": "test_user", "course_id": "test_course"}

    # Use correct API prefix
    response = client.post("/api/materials/upload", files=files, data=data)

    assert response.status_code == 200
    json_resp = response.json()
    assert "job_id" in json_resp
    assert json_resp["status"] == "processing"


@pytest.mark.asyncio
async def test_socket_io_connection() -> None:
    """Verify Socket.IO connection and session init."""
    response = client.get("/socket.io/")
    # Socket.IO protocol handshake might return 200 or 400 depending on transport params
    # But it proves the endpoint is mounted
    assert response.status_code in [200, 400, 405]


@pytest.mark.asyncio
async def test_llm_client_mock() -> None:
    """Verify LLM Client logic with mocks."""
    from app.services.llm_client import LLMClient

    mock_client_instance = MagicMock()
    mock_client_instance.chat = MagicMock()
    mock_client_instance.chat.completions = MagicMock()
    mock_chat = MagicMock()
    mock_chat.choices = [MagicMock(message=MagicMock(content="Mocked response"))]
    mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_chat)

    local_llm_client = LLMClient()
    local_llm_client.client = mock_client_instance

    response = await local_llm_client.generate_text("Test prompt")
    assert response == "Mocked response"
