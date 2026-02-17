import sys
from unittest.mock import MagicMock, patch
import os

# Mock dependencies that might be missing or heavy
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["transformers"] = MagicMock()
sys.modules["torch"] = MagicMock()
sys.modules["torchvision"] = MagicMock()
# sys.modules["numpy"] = MagicMock()  # numpy is installed

# Mock groq and other AI clients
sys.modules["groq"] = MagicMock()
sys.modules["groq.types"] = MagicMock()
sys.modules["groq.types.chat"] = MagicMock()
sys.modules["langgraph"] = MagicMock()
sys.modules["langchain"] = MagicMock()
sys.modules["langchain_google_genai"] = MagicMock()
sys.modules["ddgs"] = MagicMock()
sys.modules["deepgram"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["faster_whisper"] = MagicMock()
sys.modules["elevenlabs"] = MagicMock()
sys.modules["websockets"] = MagicMock()

# Mock app.api.ws to avoid loading it and its dependencies (langgraph etc)
mock_ws = MagicMock()
mock_ws.sio = MagicMock()
sys.modules["app.api.ws"] = mock_ws

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

    with patch.dict("app.api.materials.upload_status", test_data, clear=True):
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

def test_list_materials_server_error():
    """Test that the endpoint returns 500 when an exception occurs."""
    # Mock upload_status.values() to raise an exception
    # Since upload_status is a dict, we can't easily mock .values() directly unless we replace the object
    # But it's imported into app.api.materials, so we can patch it there.

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
        response = client.get(f"/api/materials/list", params={"user_id": user_id, "course_id": course_id})

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["materials"][0]["filename"] == "code.cpp"

def test_list_materials_partial_data():
    """Test behavior when internal data is missing optional fields (e.g. course_id)."""
    # Entry with user_id but missing course_id
    # This simulates a potential data corruption or legacy data issue
    partial_data = {
        "job_partial": {
            "job_id": "job_partial",
            "status": "completed",
            "filename": "partial.pdf",
            "user_id": "user1",
            # course_id is missing
        }
    }

    with patch.dict("app.api.materials.upload_status", partial_data, clear=True):
        # Case 1: List without course_id filter
        # Should succeed because 'course_id is None' short-circuits the check
        response = client.get("/api/materials/list?user_id=user1")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["materials"][0]["job_id"] == "job_partial"

        # Case 2: List WITH course_id filter
        # Should fail with 500 because status["course_id"] is accessed and raises KeyError
        response = client.get("/api/materials/list?user_id=user1&course_id=math101")
        assert response.status_code == 500
        data = response.json()
        assert "List failed" in data["detail"]
        assert "'course_id'" in data["detail"]
