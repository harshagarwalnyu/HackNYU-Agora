
import sys
import asyncio
import time
import os
from unittest.mock import MagicMock, patch
import pytest

# Set dummy API key to pass Settings validation during import
os.environ["GROQ_API_KEY"] = "dummy"

# Mock heavy dependencies in sys.modules to avoid installation issues and speed up tests
# This must happen BEFORE importing app modules that use them
sys.modules["groq"] = MagicMock()
sys.modules["groq.types"] = MagicMock()
sys.modules["groq.types.chat"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["torch"] = MagicMock()
sys.modules["numpy"] = MagicMock()

# Import LLMClient after mocking
from app.services.llm_client import LLMClient

@pytest.fixture
def mock_settings():
    with patch("app.services.llm_client.settings") as mock:
        mock.groq_api_key = "test_api_key"
        mock.llm_model = "test_model"
        mock.llm_temperature = 0.7
        mock.llm_max_tokens = 100
        yield mock

@pytest.fixture
def mock_sentence_transformer():
    with patch("app.services.llm_client.SentenceTransformer") as mock:
        yield mock

async def monitor_loop(stop_event):
    """Monitors the event loop latency."""
    max_latency = 0
    while not stop_event.is_set():
        start = time.time()
        # Sleep for a short interval. If the loop is blocked, this sleep will take longer.
        await asyncio.sleep(0.01)
        latency = (time.time() - start) - 0.01
        if latency > max_latency:
            max_latency = latency
    return max_latency

@pytest.mark.asyncio
async def test_embed_text_is_non_blocking(mock_settings, mock_sentence_transformer):
    """
    Verify that embed_text runs in an executor and does not block the event loop.
    """
    client = LLMClient()

    # Mock the embedding model instance
    mock_st_instance = MagicMock()
    mock_sentence_transformer.return_value = mock_st_instance

    # Mock encode to simulate a slow but GIL-releasing operation (like I/O or C++ heavy task)
    # time.sleep releases the GIL, so it's a good proxy for a heavy task running in a thread.
    def slow_encode(text):
        time.sleep(0.5)
        # Return a mock that has a .tolist() method
        mock_res = MagicMock()
        mock_res.tolist.return_value = [0.1, 0.2, 0.3]
        return mock_res

    mock_st_instance.encode.side_effect = slow_encode

    # Initialize client (this also runs in executor, so it should be fast/non-blocking if mocked correctly)
    await client.initialize()

    # Setup loop monitoring
    stop_event = asyncio.Event()
    monitor_task = asyncio.create_task(monitor_loop(stop_event))

    # Measure total execution time
    start_time = time.time()
    result = await client.embed_text("test text")
    end_time = time.time()

    # Stop monitoring
    stop_event.set()
    max_latency = await monitor_task

    # Assertions
    duration = end_time - start_time
    print(f"Duration: {duration:.4f}s, Max Latency: {max_latency:.4f}s")

    # The operation should take at least 0.5s
    assert duration >= 0.5

    # The loop latency should be small (significantly less than the operation time)
    # If it was blocking, max_latency would be around 0.5s
    # We allow some overhead, but 0.1s is a safe upper bound for a 10ms sleep.
    assert max_latency < 0.1, f"Event loop was blocked! Latency: {max_latency:.4f}s"

    assert result == [0.1, 0.2, 0.3]
    mock_st_instance.encode.assert_called_once_with("test text")
