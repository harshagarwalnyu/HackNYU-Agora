import pytest
import os
from unittest.mock import AsyncMock, patch

# Set environment variable for Settings
os.environ["GROQ_API_KEY"] = "mock_key"

# -----------------------------------------------------------------------------
# 2. Import app modules
# -----------------------------------------------------------------------------

# Patch initialize methods
with patch("app.services.qdrant_client.QdrantService.initialize", AsyncMock()), \
     patch("app.services.llm_client.LLMClient.initialize", AsyncMock()), \
     patch("app.services.stt_service.GroqWhisperSTT.initialize", AsyncMock()), \
     patch("app.services.tts_service.EdgeTTS.initialize", AsyncMock()):

    from app.main import app
    from app.api.materials import upload_status
    from app.config import settings

from fastapi.testclient import TestClient

client = TestClient(app)

# -----------------------------------------------------------------------------
# 3. Tests
# -----------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_test_storage(tmp_path):
    """Setup a temporary storage path for tests."""
    original_storage_path = settings.storage_path
    settings.storage_path = tmp_path
    yield
    settings.storage_path = original_storage_path
    # Clear upload_status between tests
    upload_status.clear()

@pytest.fixture
def mock_process_document():
    """Mock the process_document background task."""
    p = patch("app.api.materials.process_document", AsyncMock())
    m = p.start()
    yield m
    p.stop()

@pytest.mark.asyncio
async def test_upload_status_limit(mock_process_document):
    """Test that upload_status does not exceed the configured limit."""

    # Set limit to 5
    with patch.object(settings, "upload_status_history_size", 5):
        assert settings.upload_status_history_size == 5

        # Upload 10 files
        for i in range(10):
            filename = f"file_{i}.txt"
            files = {"file": (filename, b"content", "text/plain")}
            data = {"user_id": "user1", "course_id": "course1"}

            response = client.post("/api/materials/upload", files=files, data=data)
            assert response.status_code == 200

            # Verify size doesn't exceed 5
            # After each insert, size should be <= 5
            assert len(upload_status) <= 5

        # Final verification
        assert len(upload_status) == 5

        # Verify that the oldest ones (0-4) are gone and newest (5-9) are present
        filenames_in_status = [s["filename"] for s in upload_status.values()]

        for i in range(5):
            assert f"file_{i}.txt" not in filenames_in_status

        for i in range(5, 10):
            assert f"file_{i}.txt" in filenames_in_status
