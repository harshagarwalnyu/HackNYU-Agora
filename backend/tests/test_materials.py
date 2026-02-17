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


# Now we can safely import the app modules
# We still need to mock the service instances in app.services.* before app.main imports them
# But app.main imports app.services.* which instantiates the classes.
# The instantiation uses the mocked classes above.

# However, the singletons `qdrant_service` and `llm_client` are created at module level.
# We can just let them be created with the mocked dependencies,
# OR we can mock the singletons themselves if we want to be sure.

# Let's import the services and mock their methods.
# Note: Since we mocked the dependencies, the instantiation should succeed (or we might need to handle __init__ logic).

# In app/services/qdrant_client.py:
# self.client = QdrantClient(...) -> uses our mock
# In app/services/llm_client.py:
# self.client = AsyncGroq(...) -> uses our mock

# So we can just import them and then mock the methods on the singletons.

from app.services.qdrant_client import qdrant_service
from app.services.llm_client import llm_client

qdrant_service.initialize = AsyncMock()
qdrant_service.close = AsyncMock()
qdrant_service.upsert_notes = AsyncMock()
qdrant_service.health_check = AsyncMock(return_value=True)

llm_client.initialize = AsyncMock()
llm_client.close = AsyncMock()
llm_client.health_check = AsyncMock(return_value=True)
llm_client.generate_text = AsyncMock(return_value="Mocked LLM generation")

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

@pytest.mark.asyncio
async def test_upload_file_too_large(tmp_path):
    """Test that uploading a file larger than the limit returns 413."""
    # Set max size to a small value (e.g., 10 bytes)
    with patch.object(settings, 'upload_max_size', new=10):
        # Use temporary storage path
        with patch.object(settings, 'storage_path', new=tmp_path):
            # Create a file content larger than 10 bytes
            file_content = b"This is definitely more than 10 bytes."
            files = {"file": ("large_file.txt", file_content, "text/plain")}
            data = {"user_id": "test_user", "course_id": "test_course"}

            response = client.post("/api/materials/upload", files=files, data=data)

            assert response.status_code == 413
            assert "File too large" in response.json()["detail"]

@pytest.mark.asyncio
async def test_upload_file_within_limit(tmp_path):
    """Test that uploading a valid file returns 200."""
    # Set max size to a large value
    with patch.object(settings, 'upload_max_size', new=1024 * 1024):
        # Use temporary storage path
        with patch.object(settings, 'storage_path', new=tmp_path):
            # Mock process_document to avoid actual processing
            with patch("app.api.materials.process_document", new_callable=AsyncMock) as mock_process:
                file_content = b"Small file content"
                files = {"file": ("small_file.txt", file_content, "text/plain")}
                data = {"user_id": "test_user", "course_id": "test_course"}

                response = client.post("/api/materials/upload", files=files, data=data)

                assert response.status_code == 200
                json_resp = response.json()
                assert json_resp["status"] == "processing"
                assert "job_id" in json_resp

                # Verify file was saved in temp path
                user_path = tmp_path / "test_user" / "test_course"
                assert user_path.exists()
                files = list(user_path.glob("*.txt"))
                assert len(files) == 1
                assert files[0].read_bytes() == file_content
