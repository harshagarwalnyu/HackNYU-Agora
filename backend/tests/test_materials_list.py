import sys
from unittest.mock import MagicMock, patch
import os

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
mock_module("torchvision")
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


# Set required environment variables
os.environ["GROQ_API_KEY"] = "mock_key"

# Force import of modules so patch can find them
# We need to explicitly import submodules that we want to patch
try:
    import app.services.qdrant_client
    import app.services.llm_client
    import app.services.stt_service
    import app.services.tts_service
except ImportError as e:
    print(f"Failed to import services: {e}")
    # We continue, assuming that if import failed it's because of some other dependency
    # but since we mocked most things, it should be fine.

# Mock services before importing app
with patch("app.services.qdrant_client.QdrantService.initialize", new_callable=MagicMock), \
     patch("app.services.llm_client.LLMClient.initialize", new_callable=MagicMock), \
     patch("app.services.stt_service.GroqWhisperSTT.initialize", new_callable=MagicMock), \
     patch("app.services.tts_service.EdgeTTS.initialize", new_callable=MagicMock):

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
    with patch("app.api.materials.upload_status", MagicMock()) as mock_status:
        # Mocking values() on a dict mock requires some care.
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
