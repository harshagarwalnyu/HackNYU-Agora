import sys
from unittest.mock import MagicMock, patch
import os

# Mock dependencies that might be missing or heavy
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["transformers"] = MagicMock()
sys.modules["torch"] = MagicMock()
sys.modules["torchvision"] = MagicMock()
# sys.modules["numpy"] = MagicMock()  # numpy is installed

# Set required environment variables
os.environ["GROQ_API_KEY"] = "mock_key"

# Force import of modules so patch can find them
import app.services.qdrant_client
import app.services.llm_client
import app.services.stt_service
import app.services.tts_service

# Mock services before importing app
# We need to use patch for modules that are imported by app.main or its dependencies
with patch("app.services.qdrant_client.qdrant_service") as mock_qdrant, \
     patch("app.services.llm_client.llm_client") as mock_llm, \
     patch("app.services.stt_service.get_stt_service") as mock_get_stt, \
     patch("app.services.tts_service.get_tts_service") as mock_get_tts:

    # Setup service mocks
    mock_qdrant.initialize = MagicMock()
    mock_qdrant.close = MagicMock()
    mock_llm.initialize = MagicMock()
    mock_llm.close = MagicMock()

    # Setup STT mock
    mock_stt_instance = MagicMock()
    mock_stt_instance.initialize = MagicMock()
    mock_get_stt.return_value = mock_stt_instance

    # Setup TTS mock
    mock_tts_instance = MagicMock()
    mock_tts_instance.initialize = MagicMock()
    mock_get_tts.return_value = mock_tts_instance

    # Now import app and components
    from app.main import app
    from app.api.materials import upload_status

from fastapi.testclient import TestClient

client = TestClient(app)

def test_list_materials_filtering():
    """Test the list_materials endpoint with various filters."""
    # Clear existing status
    upload_status.clear()

    # Setup test data
    test_data = {
        "job1": {
            "job_id": "job1",
            "status": "completed",
            "filename": "math_notes.pdf",
            "user_id": "user1",
            "course_id": "math101",
            "progress": 100,
            "message": "Processing complete"
        },
        "job2": {
            "job_id": "job2",
            "status": "processing",
            "filename": "physics_lab.pdf",
            "user_id": "user1",
            "course_id": "phys202",
            "progress": 50,
            "message": "Processing..."
        },
        "job3": {
            "job_id": "job3",
            "status": "completed",
            "filename": "history_essay.docx",
            "user_id": "user2",
            "course_id": "hist101",
            "progress": 100,
            "message": "Processing complete"
        }
    }

    upload_status.update(test_data)

    # Test 1: List all materials for user1
    response = client.get("/api/materials/list?user_id=user1")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert len(data["materials"]) == 2
    filenames = {m["filename"] for m in data["materials"]}
    assert "math_notes.pdf" in filenames
    assert "physics_lab.pdf" in filenames
    assert "history_essay.docx" not in filenames

    # Test 2: Filter by course_id for user1
    response = client.get("/api/materials/list?user_id=user1&course_id=math101")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["materials"][0]["filename"] == "math_notes.pdf"

    # Test 3: List materials for user2
    response = client.get("/api/materials/list?user_id=user2")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["materials"][0]["filename"] == "history_essay.docx"

    # Test 4: List materials for non-existent user
    response = client.get("/api/materials/list?user_id=user3")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["materials"] == []

def test_list_materials_empty_params():
    """Test validation errors for missing parameters."""
    # Missing user_id
    response = client.get("/api/materials/list")
    assert response.status_code == 422  # Validation Error
