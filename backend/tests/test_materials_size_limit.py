import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Mock heavy dependencies in sys.modules BEFORE importing application code
# This prevents ImportErrors for missing libraries and speeds up tests
sys.modules["groq"] = MagicMock()
sys.modules["groq.types"] = MagicMock()
sys.modules["groq.types.chat"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["torch"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["transformers"] = MagicMock()
sys.modules["qdrant_client"] = MagicMock()
sys.modules["qdrant_client.http"] = MagicMock()
sys.modules["qdrant_client.http.models"] = MagicMock()
sys.modules["qdrant_client.http.exceptions"] = MagicMock()
sys.modules["docling"] = MagicMock()
sys.modules["docling.document_converter"] = MagicMock()
sys.modules["PyPDF2"] = MagicMock()
sys.modules["edge_tts"] = MagicMock()

# Now imports can proceed safely
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# We need to set placeholder env vars for Settings validation if not present
os.environ["GROQ_API_KEY"] = "mock_key"

# Import the router to test
# This will trigger imports of app.config, app.workers.chunk_ingest, etc.
# Since we mocked the heavy modules, this should succeed.
from app.api.materials import router
from app.config import settings

@pytest.fixture
def client():
    # Create a fresh app for testing
    app = FastAPI()
    app.include_router(router, prefix="/api/materials")
    return TestClient(app)

def test_upload_file_too_large(client):
    """
    Test that uploading a file larger than settings.upload_max_size
    returns a 413 Payload Too Large error.
    """
    # Mock upload_max_size to a small value (e.g., 5 bytes)
    # Since settings is a Pydantic model instance, we can patch the attribute on the instance.
    # We use patch.object on the imported settings instance.

    with patch.object(settings, "upload_max_size", 5):
        # Create a file content larger than 5 bytes
        file_content = b"123456"  # 6 bytes
        files = {"file": ("test.txt", file_content, "text/plain")}
        data = {"user_id": "test_user", "course_id": "test_course"}

        response = client.post("/api/materials/upload", files=files, data=data)

        # Assertions
        assert response.status_code == 413
        json_resp = response.json()
        assert "File too large" in json_resp["detail"]
        assert "Maximum size" in json_resp["detail"]
