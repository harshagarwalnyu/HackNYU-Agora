import pytest
import os
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
import sys

# Set required environment variables before importing config
os.environ["GROQ_API_KEY"] = "mock_groq_key"

# Mock services BEFORE importing app to handle lifespan correctly
# We need to mock the modules/instances that are imported/used in app.main

# Mock heavy ML dependencies
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["transformers"] = MagicMock()
sys.modules["torch"] = MagicMock()
sys.modules["torchvision"] = MagicMock()
sys.modules["docling"] = MagicMock()

# Mock Qdrant and LLM clients (instances)
from app.services.qdrant_client import qdrant_service
from app.services.llm_client import llm_client

qdrant_service.initialize = AsyncMock()
qdrant_service.close = AsyncMock()
qdrant_service.health_check = AsyncMock(return_value=True)

llm_client.initialize = AsyncMock()
llm_client.close = AsyncMock()
llm_client.health_check = AsyncMock(return_value=True)

# Mock STT and TTS services (factory functions used in lifespan)
# We need to patch the modules where get_stt_service/get_tts_service are defined
# so that when app.main imports them, it gets our mocks.

# Mock STT Service
import app.services.stt_service
mock_stt_instance = AsyncMock()
mock_stt_instance.initialize = AsyncMock()
mock_stt_instance.close = AsyncMock()
app.services.stt_service.get_stt_service = MagicMock(return_value=mock_stt_instance)

# Mock TTS Service
import app.services.tts_service
mock_tts_instance = AsyncMock()
mock_tts_instance.initialize = AsyncMock()
mock_tts_instance.close = AsyncMock()
app.services.tts_service.get_tts_service = MagicMock(return_value=mock_tts_instance)

# Mock chunk_ingest worker to avoid heavy dependencies (Docling, Torch, etc.)
# This prevents ImportError when app.api.materials imports process_document
mock_chunk_ingest = MagicMock()
mock_chunk_ingest.process_document = AsyncMock()
sys.modules["app.workers.chunk_ingest"] = mock_chunk_ingest

# Now import app (which triggers lifespan and router inclusion)
from app.main import app
from app.api.materials import upload_status

# Create TestClient
client = TestClient(app)

@pytest.mark.asyncio
async def test_get_upload_status_success():
    """
    Test retrieving status for an existing job.
    Verifies that the endpoint returns 200 and the correct status data.
    """
    job_id = "test_job_success_123"
    test_status = {
        "job_id": job_id,
        "status": "processing",
        "progress": 50,
        "message": "Processing halfway done",
        "user_id": "test_user",
        "course_id": "test_course"
    }

    # Inject status into the in-memory store
    upload_status[job_id] = test_status

    try:
        response = client.get(f"/api/materials/status/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "processing"
        assert data["progress"] == 50
        assert data["message"] == "Processing halfway done"
        assert data["user_id"] == "test_user"

    finally:
        # Clean up
        if job_id in upload_status:
            del upload_status[job_id]

@pytest.mark.asyncio
async def test_get_upload_status_not_found():
    """
    Test retrieving status for a non-existent job.
    Verifies that the endpoint returns 404.
    """
    job_id = "non_existent_job_id"

    # Ensure job_id is not in store
    if job_id in upload_status:
        del upload_status[job_id]

    response = client.get(f"/api/materials/status/{job_id}")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Job not found"
