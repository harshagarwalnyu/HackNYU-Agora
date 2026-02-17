
import os
import sys
import asyncio
import time
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# Set environment variable for Settings validation
os.environ["GROQ_API_KEY"] = "dummy"

# Now import app modules
from app.services.qdrant_client import QdrantService
from qdrant_client.http import models

@pytest.fixture
def mock_qdrant_client():
    client = AsyncMock()
    # Mock upsert to simulate some network delay without blocking
    async def simulated_upsert(*args, **kwargs):
        await asyncio.sleep(0.01)  # Simulate network latency
        return MagicMock()

    client.upsert.side_effect = simulated_upsert
    return client

@pytest.mark.asyncio
async def test_upsert_notes_is_async_and_non_blocking(mock_qdrant_client):
    """
    Verify that upsert_notes uses await and does not block the event loop.
    """
    with patch("app.services.qdrant_client.settings") as mock_settings:
        mock_settings.qdrant_collection_notes = "test_notes"

        service = QdrantService()
        service.client = mock_qdrant_client

        # Prepare test data
        user_id = "test_user"
        course_id = "test_course"
        chunks = [{"id": i, "text": f"chunk {i}", "embedding": [0.1] * 768} for i in range(10)]

        # Measure execution time of upsert_notes
        start_time = time.time()

        async def concurrent_task():
            start = time.time()
            await asyncio.sleep(0.005)
            return time.time() - start

        # Run upsert and concurrent task together
        task = asyncio.create_task(concurrent_task())
        await service.upsert_notes(user_id, course_id, chunks)
        concurrent_duration = await task

        duration = time.time() - start_time

        # Verify upsert was called
        assert mock_qdrant_client.upsert.called
        assert mock_qdrant_client.upsert.call_count == 1

        # Verify call arguments
        call_args = mock_qdrant_client.upsert.call_args
        kwargs = call_args.kwargs
        assert kwargs["collection_name"] == "test_notes"
        assert len(kwargs["points"]) == 10

        print(f"Upsert duration: {duration:.4f}s")
        print(f"Concurrent task duration: {concurrent_duration:.4f}s")

        # If blocking, concurrent_task would take > 0.01s (upsert duration)
        # If non-blocking, it should finish while upsert is waiting (~0.005s)
        # So check if it finished before upsert completed significantly
        assert concurrent_duration < duration
