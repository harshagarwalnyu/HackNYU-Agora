
import pytest
from unittest.mock import patch
from app.services.qdrant_client import QdrantService

@pytest.fixture
def mock_settings():
    with patch("app.services.qdrant_client.settings") as mock_settings:
        mock_settings.qdrant_url = ":memory:"
        mock_settings.qdrant_api_key = None
        mock_settings.qdrant_collection_notes = "test_notes"
        mock_settings.qdrant_collection_memory = "test_memory"
        mock_settings.qdrant_vector_size = 4
        yield mock_settings

@pytest.mark.asyncio
async def test_qdrant_service_flow(mock_settings):
    """Test full flow of QdrantService with in-memory AsyncQdrantClient."""
    service = QdrantService()

    # Initialize
    await service.initialize()
    assert service.client is not None
    assert hasattr(service.client, "get_collections")

    # Check collections
    collections = await service.client.get_collections()
    collection_names = [c.name for c in collections.collections]
    assert mock_settings.qdrant_collection_notes in collection_names
    assert mock_settings.qdrant_collection_memory in collection_names

    # Upsert notes
    user_id = "user1"
    course_id = "course1"
    chunks = [
        {
            "id": 1,
            "text": "This is a test note",
            "embedding": [0.1, 0.2, 0.3, 0.4],
            "metadata": {"page": 1}
        },
        {
            "id": 2,
            "text": "Another note",
            "embedding": [0.4, 0.3, 0.2, 0.1],
            "metadata": {"page": 2}
        }
    ]

    await service.upsert_notes(user_id, course_id, chunks)

    # Verify upsert (direct client check)
    count = await service.client.count(
        collection_name=mock_settings.qdrant_collection_notes
    )
    assert count.count == 2

    # Search notes
    query_embedding = [0.1, 0.2, 0.3, 0.4]
    results = await service.search_notes(query_embedding, user_id, course_id)

    assert len(results) > 0
    assert results[0]["id"] == 1
    assert results[0]["score"] >= 0.99  # Should be close to 1 for identical vector

    # Upsert memory
    session_id = "session1"
    memory_data = {"mastered": ["topic1"], "confused": []}
    memory_embedding = [0.5, 0.5, 0.5, 0.5]

    await service.upsert_memory(user_id, session_id, memory_data, memory_embedding)

    # Get memory
    memories = await service.get_memory(user_id)
    assert len(memories) == 1
    assert memories[0]["session_id"] == session_id
    assert memories[0]["memory_data"] == memory_data

    # Close
    await service.close()
    assert service.client is None

@pytest.mark.asyncio
async def test_health_check(mock_settings):
    service = QdrantService()

    # Not initialized
    assert await service.health_check() is False

    # Initialized
    await service.initialize()
    assert await service.health_check() is True

    await service.close()
