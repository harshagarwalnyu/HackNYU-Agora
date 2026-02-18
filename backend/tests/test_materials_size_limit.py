import os
from unittest.mock import patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# We need to set placeholder env vars for Settings validation if not present
os.environ["GROQ_API_KEY"] = "mock_key"

# Import the router to test
# This will trigger imports of app.config, app.chunk_ingest, etc.
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
