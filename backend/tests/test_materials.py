import pytest
import os
from unittest.mock import MagicMock, AsyncMock, patch

# Set environment variable for Settings
os.environ["GROQ_API_KEY"] = "mock_key"

# -----------------------------------------------------------------------------
# 2. Import app modules
# -----------------------------------------------------------------------------

# Import services manually to ensure they are loaded and patch targets exist
try:
    import app.config
    import app.services.qdrant_client
    import app.services.llm_client
    import app.services.stt_service
    import app.services.tts_service
except ImportError as e:
    print(f"Failed to import services: {e}")
    import traceback
    traceback.print_exc()

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
    p1 = patch("app.api.materials.process_document", AsyncMock())
    p2 = patch("app.chunk_ingest.process_document", AsyncMock())

    m1 = p1.start()
    p2.start()

    yield m1  # We use the one in materials for assertions

    p1.stop()
    p2.stop()

@pytest.mark.asyncio
async def test_upload_materials_success(mock_process_document):
    """
    Test successful material upload triggering background task.
    """
    filename = "lecture_notes.pdf"
    file_content = b"%PDF-1.4 content..."
    user_id = "student_01"
    course_id = "history_101"

    files = {"file": (filename, file_content, "application/pdf")}
    data = {
        "user_id": user_id,
        "course_id": course_id,
        "description": "Notes from week 1"
    }

    response = client.post("/api/materials/upload", files=files, data=data)

    assert response.status_code == 200, f"Response: {response.text}"
    json_resp = response.json()

    assert json_resp["status"] == "processing"
    job_id = json_resp["job_id"]

    # Verify file exists
    expected_path = settings.storage_path / user_id / course_id / f"{job_id}.pdf"
    assert expected_path.exists()
    assert expected_path.read_bytes() == file_content

    # Verify mock called
    mock_process_document.assert_called_once()

    call_kwargs = mock_process_document.call_args.kwargs
    assert call_kwargs["user_id"] == user_id
    assert call_kwargs["job_id"] == job_id
    assert str(expected_path) == call_kwargs["file_path"]

@pytest.mark.asyncio
async def test_upload_materials_path_traversal(mock_process_document):
    """Test that path traversal attempts are blocked."""
    files = {"file": ("test.txt", b"content", "text/plain")}

    # Case 1: user_id traversal
    data = {"user_id": "../root", "course_id": "c1"}
    response = client.post("/api/materials/upload", files=files, data=data)
    assert response.status_code in [403, 400], f"Expected 403/400, got {response.status_code}: {response.text}"

    # Case 2: course_id traversal
    # user_id adds one level, so we need ../../ to break out
    data = {"user_id": "u1", "course_id": "../../etc"}
    response = client.post("/api/materials/upload", files=files, data=data)
    assert response.status_code in [403, 400], f"Expected 403/400, got {response.status_code}: {response.text}"

    # Ensure background task was NOT called
    mock_process_document.assert_not_called()

@pytest.mark.asyncio
async def test_upload_file_too_large(mock_process_document):
    """Test upload with file exceeding max size."""
    # Mock settings.upload_max_size
    with patch.object(settings, "upload_max_size", 10): # 10 bytes
        files = {"file": ("test.txt", b"too large content", "text/plain")}
        data = {"user_id": "u1", "course_id": "c1"}

        response = client.post("/api/materials/upload", files=files, data=data)
        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]

    # Ensure background task was NOT called
    mock_process_document.assert_not_called()

def test_upload_materials_no_filename():
    """Test upload with no filename."""
    files = {"file": ("", b"content", "text/plain")}
    data = {"user_id": "user123"}

    response = client.post("/api/materials/upload", files=files, data=data)
    # FastAPI might return 422 if it validates empty filename, or 400 if our check catches it
    assert response.status_code in [400, 422], f"Response: {response.text}"
    # If 400, we expect our message. If 422, it's a validation error.
    if response.status_code == 400:
        assert response.json()["detail"] == "No filename provided"

def test_upload_materials_server_error():
    """Test server error during upload."""
    # We patch builtins.open to simulate disk error
    with patch("builtins.open", side_effect=Exception("Disk full")):
        files = {"file": ("test.txt", b"content", "text/plain")}
        data = {"user_id": "user123"}

        response = client.post("/api/materials/upload", files=files, data=data)
        assert response.status_code == 500
        assert "Upload failed" in response.json()["detail"]

def test_get_upload_status_success():
    """Test getting upload status for an existing job."""
    job_id = "test-job-123"
    upload_status[job_id] = {
        "job_id": job_id,
        "status": "completed",
        "progress": 100,
        "message": "Processing complete",
        "user_id": "user1",
        "course_id": "course1"
    }

    response = client.get(f"/api/materials/status/{job_id}")
    assert response.status_code == 200
    assert response.json() == upload_status[job_id]

def test_get_upload_status_not_found():
    """Test getting status for a non-existent job."""
    response = client.get("/api/materials/status/non-existent-job")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"

def test_list_materials_success():
    """Test listing materials for a user."""
    upload_status["job1"] = {"job_id": "job1", "user_id": "user1", "course_id": "course1", "status": "completed"}
    upload_status["job2"] = {"job_id": "job2", "user_id": "user1", "course_id": "course2", "status": "processing"}
    upload_status["job3"] = {"job_id": "job3", "user_id": "user2", "course_id": "course1", "status": "completed"}

    response = client.get("/api/materials/list?user_id=user1")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["count"] == 2
    assert len(json_resp["materials"]) == 2
    job_ids = [m["job_id"] for m in json_resp["materials"]]
    assert "job1" in job_ids
    assert "job2" in job_ids
    assert "job3" not in job_ids

def test_list_materials_with_course_filter():
    """Test listing materials with course filter."""
    upload_status["job1"] = {"job_id": "job1", "user_id": "user1", "course_id": "course1", "status": "completed"}
    upload_status["job2"] = {"job_id": "job2", "user_id": "user1", "course_id": "course2", "status": "processing"}

    response = client.get("/api/materials/list?user_id=user1&course_id=course1")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["count"] == 1
    assert json_resp["materials"][0]["job_id"] == "job1"

def test_list_materials_empty():
    """Test listing materials when none exist for user."""
    response = client.get("/api/materials/list?user_id=unknown")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["count"] == 0
    assert json_resp["materials"] == []

def test_list_materials_empty_params():
    """Test validation errors for missing parameters."""
    # Missing user_id
    response = client.get("/api/materials/list")
    assert response.status_code == 422  # Validation Error

def test_list_materials_server_error():
    """Test that the endpoint returns 500 when an exception occurs."""
    # Mock upload_status.values() to raise an exception
    # We patch the object in the module where it is used
    with patch("app.api.materials.upload_status", MagicMock()) as mock_status:
        mock_status.values.side_effect = Exception("Database connection lost")

        response = client.get("/api/materials/list?user_id=user1")

        assert response.status_code == 500
        data = response.json()
        assert "List failed" in data["detail"]
        assert "Database connection lost" in data["detail"]

def test_list_materials_malformed_data():
    """Test behavior when internal data is malformed (missing keys)."""
    # Add an entry missing 'user_id' which will cause KeyError during iteration
    malformed_data = {
        "bad_job": {
            "job_id": "bad_job",
            "status": "processing",
            # Missing user_id and course_id
        }
    }

    # We use patch.dict because upload_status is a global dict
    with patch.dict("app.api.materials.upload_status", malformed_data, clear=True):
        response = client.get("/api/materials/list?user_id=user1")

        assert response.status_code == 500
        data = response.json()
        # The error message should mention the missing key
        assert "KeyError" in data["detail"] or "'user_id'" in data["detail"]

def test_list_materials_special_chars():
    """Test handling of special characters in parameters."""
    user_id = "user test@example.com"
    course_id = "C++ Advanced"

    test_data = {
        "job_special": {
            "job_id": "job_special",
            "status": "completed",
            "filename": "code.cpp",
            "user_id": user_id,
            "course_id": course_id,
            "progress": 100,
            "message": "Done"
        }
    }

    with patch.dict("app.api.materials.upload_status", test_data, clear=True):
        # URL encoded parameters handled by TestClient/FastAPI
        response = client.get("/api/materials/list", params={"user_id": user_id, "course_id": course_id})

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["materials"][0]["filename"] == "code.cpp"
