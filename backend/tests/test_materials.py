import sys
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

# Mock external dependencies that might be missing or hard to install
# We mock them BEFORE importing the app modules

# Mock qdrant_client
mock_qdrant = MagicMock()
sys.modules["qdrant_client"] = mock_qdrant
sys.modules["qdrant_client.http"] = MagicMock()
sys.modules["qdrant_client.http.models"] = MagicMock()
sys.modules["qdrant_client.http.exceptions"] = MagicMock()

# Mock groq
mock_groq = MagicMock()
sys.modules["groq"] = mock_groq
sys.modules["groq.types"] = MagicMock()
sys.modules["groq.types.chat"] = MagicMock()

# Mock sentence_transformers
mock_sentence_transformers = MagicMock()
sys.modules["sentence_transformers"] = mock_sentence_transformers

# Mock edge_tts
mock_edge_tts = MagicMock()
sys.modules["edge_tts"] = mock_edge_tts

# Mock langgraph
mock_langgraph = MagicMock()
sys.modules["langgraph"] = mock_langgraph
sys.modules["langgraph.graph"] = MagicMock()
sys.modules["langgraph.graph.state"] = MagicMock()

# Mock specific imports used in services
# We need to make sure that when 'from qdrant_client import QdrantClient' runs, it works
mock_qdrant.QdrantClient = MagicMock()
mock_groq.AsyncGroq = MagicMock()
mock_sentence_transformers.SentenceTransformer = MagicMock()

# Mock service instances and initialization before app import
with patch("app.services.qdrant_client.QdrantService.initialize", AsyncMock()), \
     patch("app.services.llm_client.LLMClient.initialize", AsyncMock()), \
     patch("app.services.stt_service.GroqWhisperSTT.initialize", AsyncMock()):
    # We must also mock edge_tts if it is imported at top level in tts_service
    # But since we mocked sys.modules['edge_tts'], the import should succeed.

    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.materials import upload_status
    from app.config import settings

client = TestClient(app)

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
    with patch("app.api.materials.process_document", AsyncMock()) as mock:
        yield mock

@pytest.mark.asyncio
async def test_upload_materials_success(mock_process_document):
    """Test successful material upload."""
    content = b"test content"
    files = {"file": ("test.txt", content, "text/plain")}
    data = {"user_id": "user123", "course_id": "course456", "description": "test desc"}

    response = client.post("/api/materials/upload", files=files, data=data)

    assert response.status_code == 200
    json_resp = response.json()
    assert "job_id" in json_resp
    job_id = json_resp["job_id"]
    assert json_resp["status"] == "processing"

    # Check if status was updated in-memory
    assert job_id in upload_status
    assert upload_status[job_id]["user_id"] == "user123"
    assert upload_status[job_id]["course_id"] == "course456"

    # Check if file was saved
    saved_file_path = settings.storage_path / "user123" / "course456" / f"{job_id}.txt"
    assert saved_file_path.exists()
    with open(saved_file_path, "rb") as f:
        assert f.read() == content

def test_upload_materials_no_filename():
    """Test upload with no filename."""
    files = {"file": ("", b"content", "text/plain")}
    data = {"user_id": "user123"}

    response = client.post("/api/materials/upload", files=files, data=data)
    # FastAPI/Starlette might return 422 Unprocessable Entity for invalid file parts
    # or our code returns 400.
    assert response.status_code in [400, 422]
    if response.status_code == 400:
        assert response.json()["detail"] == "No filename provided"

def test_upload_materials_file_too_large():
    """Test upload with file exceeding max size."""
    # We use app.config.settings directly because app.api.materials imports settings from there
    with patch.object(settings, 'upload_max_size', new=5):
        files = {"file": ("test.txt", b"too large content", "text/plain")}
        data = {"user_id": "user123"}

        response = client.post("/api/materials/upload", files=files, data=data)
        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]

def test_upload_materials_server_error():
    """Test server error during upload."""
    with patch("app.api.materials.open", side_effect=Exception("Disk full")):
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
