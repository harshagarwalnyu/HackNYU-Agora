
import sys
import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Set environment variable for Settings
os.environ["GROQ_API_KEY"] = "dummy_key_for_test"

# -----------------------------------------------------------------------------
# 1. Mock heavy/missing dependencies in sys.modules BEFORE importing app modules
# -----------------------------------------------------------------------------

def mock_module(name):
    if name in sys.modules:
        return sys.modules[name]
    mock = MagicMock()
    sys.modules[name] = mock
    return mock

# Mock external services and libraries
mock_groq = mock_module("groq")
mock_groq.AsyncGroq = MagicMock()

mock_groq_types = mock_module("groq.types")
mock_groq_chat = mock_module("groq.types.chat")

# Sentence Transformers & Torch
mock_st = mock_module("sentence_transformers")
mock_st.SentenceTransformer = MagicMock()
mock_module("torch")
mock_module("numpy")

# Docling
mock_docling = mock_module("docling")
mock_docling_converter = mock_module("docling.document_converter")

# Qdrant
mock_qdrant = mock_module("qdrant_client")
mock_qdrant.AsyncQdrantClient = MagicMock()
mock_qdrant_http = mock_module("qdrant_client.http")
mock_qdrant_models = mock_module("qdrant_client.http.models")
mock_qdrant_exceptions = mock_module("qdrant_client.http.exceptions")
mock_qdrant_exceptions.UnexpectedResponse = Exception

# TTS / STT / Other
mock_module("edge_tts")
mock_module("google.generativeai")
mock_module("langgraph")
mock_module("langchain")
mock_module("langchain_google_genai")
mock_module("ddgs")
mock_module("deepgram")
mock_module("openai")
mock_module("faster_whisper")
mock_module("elevenlabs")
mock_module("websockets")

# Mock app.api.ws to avoid loading it and its dependencies
mock_ws = mock_module("app.api.ws")
mock_ws.sio = MagicMock()

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
    p2 = patch("app.workers.chunk_ingest.process_document", AsyncMock())

    m1 = p1.start()
    m2 = p2.start()

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
