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

from app.main import app  # noqa: E402

# Create TestClient
client = TestClient(app)


@pytest.mark.asyncio
async def test_health_check():
    """Verify backend health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["status"] == "healthy"
    assert json_resp["services"]["qdrant"] == "healthy"
    assert json_resp["services"]["llm"] == "healthy"


@pytest.mark.asyncio
async def test_materials_upload_flow():
    """Verify file upload flow."""
    # Create dummy file
    files = {"file": ("test.txt", b"dummy content", "text/plain")}
    data = {"user_id": "test_user", "course_id": "test_course"}

    # Use correct API prefix
    response = client.post("/api/materials/upload", files=files, data=data)

    assert response.status_code == 200
    json_resp = response.json()
    assert "job_id" in json_resp
    assert json_resp["status"] == "processing"


@pytest.mark.asyncio
async def test_socket_io_connection():
    """Verify Socket.IO connection and session init."""
    response = client.get("/socket.io/")
    # Socket.IO protocol handshake might return 200 or 400 depending on transport params
    # But it proves the endpoint is mounted
    assert response.status_code in [200, 400, 405]


@pytest.mark.asyncio
async def test_llm_client_mock():
    """Verify LLM Client logic with mocks."""
    from app.services.llm_client import LLMClient

    # Patch the AsyncGroq imported in llm_client module
    with patch("app.services.llm_client.AsyncGroq") as MockGroq:
        # Setup mock client
        mock_client_instance = AsyncMock()
        MockGroq.return_value = mock_client_instance

        # Setup mock chat completion
        mock_chat = AsyncMock()
        mock_chat.choices = [MagicMock(message=MagicMock(content="Mocked response"))]
        mock_client_instance.chat.completions.create.return_value = mock_chat

        # Instantiate separate LLMClient for unit testing logic
        local_llm_client = LLMClient()
        await local_llm_client.initialize()

        # Verify initial generation
        print("Generating text...")
        response = await local_llm_client.generate_text("Test prompt")
        print(f"Response: {response}")
        assert response == "Mocked response"
