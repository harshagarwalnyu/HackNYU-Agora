import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Mock heavy dependencies in sys.modules to avoid installation issues and speed up tests
# This must happen BEFORE importing app modules that use them
sys.modules["groq"] = MagicMock()
sys.modules["groq.types"] = MagicMock()
sys.modules["groq.types.chat"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()
# torch and numpy are often required by sentence_transformers
sys.modules["torch"] = MagicMock()
sys.modules["numpy"] = MagicMock()

import pytest
import pytest_asyncio
import asyncio
import json
import base64

# Now import LLMClient. Since we mocked the modules, the imports inside will succeed using the mocks.
# However, we need to ensure that the mocked modules provide the classes we expect.
# For example, `from groq import AsyncGroq` will get `sys.modules["groq"].AsyncGroq`.
# `MagicMock` automatically creates attributes on access, so this should work.

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
def mock_groq():
    with patch("app.services.llm_client.AsyncGroq") as mock:
        yield mock

@pytest.fixture
def mock_sentence_transformer():
    with patch("app.services.llm_client.SentenceTransformer") as mock:
        yield mock

@pytest_asyncio.fixture
async def llm_client(mock_settings, mock_groq, mock_sentence_transformer):
    client = LLMClient()
    # Ensure we start fresh
    client.client = None
    client.embedding_model = None
    return client

@pytest.mark.asyncio
async def test_initialize(llm_client, mock_groq, mock_sentence_transformer):
    await llm_client.initialize()

    mock_groq.assert_called_once_with(api_key="test_api_key")
    mock_sentence_transformer.assert_called_once_with("all-MiniLM-L6-v2")

    assert llm_client.client is not None
    assert llm_client.embedding_model is not None

@pytest.mark.asyncio
async def test_initialize_failure(llm_client, mock_groq):
    mock_groq.side_effect = Exception("Init failed")

    with pytest.raises(Exception, match="Init failed"):
        await llm_client.initialize()

@pytest.mark.asyncio
async def test_close(llm_client, mock_groq, mock_sentence_transformer):
    # Setup
    mock_groq_instance = AsyncMock()
    mock_groq.return_value = mock_groq_instance
    await llm_client.initialize()

    await llm_client.close()

    mock_groq_instance.close.assert_called_once()
    assert llm_client.client is None
    assert llm_client.embedding_model is None

@pytest.mark.asyncio
async def test_health_check_success(llm_client, mock_groq):
    mock_groq_instance = AsyncMock()
    mock_groq.return_value = mock_groq_instance
    await llm_client.initialize()

    assert await llm_client.health_check() is True

    mock_groq_instance.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_health_check_failure(llm_client, mock_groq):
    mock_groq_instance = AsyncMock()
    # Mock create to raise exception
    mock_groq_instance.chat.completions.create.side_effect = Exception("API Error")
    mock_groq.return_value = mock_groq_instance
    await llm_client.initialize()

    assert await llm_client.health_check() is False

@pytest.mark.asyncio
async def test_health_check_uninitialized(llm_client):
    assert await llm_client.health_check() is False

@pytest.mark.asyncio
async def test_generate_text_success(llm_client, mock_groq):
    mock_groq_instance = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Generated text"))]
    mock_groq_instance.chat.completions.create.return_value = mock_response
    mock_groq.return_value = mock_groq_instance

    await llm_client.initialize()

    result = await llm_client.generate_text("Test prompt")
    assert result == "Generated text"

    mock_groq_instance.chat.completions.create.assert_called_once()
    call_kwargs = mock_groq_instance.chat.completions.create.call_args.kwargs
    assert call_kwargs["messages"] == [{"role": "user", "content": "Test prompt"}]
    assert call_kwargs["model"] == "test_model"

@pytest.mark.asyncio
async def test_generate_text_uninitialized(llm_client):
    with pytest.raises(RuntimeError, match="LLM client not initialized"):
        await llm_client.generate_text("Test prompt")

@pytest.mark.asyncio
async def test_generate_json_success(llm_client, mock_groq):
    mock_groq_instance = AsyncMock()
    # Return JSON string wrapped in code block
    json_content = '```json\n{"key": "value"}\n```'
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=json_content))]
    mock_groq_instance.chat.completions.create.return_value = mock_response
    mock_groq.return_value = mock_groq_instance

    await llm_client.initialize()

    result = await llm_client.generate_json("Test prompt")
    assert result == {"key": "value"}

    # Verify system prompt includes JSON instruction
    call_kwargs = mock_groq_instance.chat.completions.create.call_args.kwargs
    messages = call_kwargs["messages"]
    system_msg = next((m for m in messages if m["role"] == "system"), None)
    assert system_msg is not None
    assert "IMPORTANT: You must respond with valid JSON only" in system_msg["content"]

@pytest.mark.asyncio
async def test_embed_text_success(llm_client, mock_sentence_transformer):
    mock_st_instance = MagicMock()
    # Mock encode to return a numpy-like object or list
    # The code calls .tolist() on the result.
    mock_embedding = MagicMock()
    mock_embedding.tolist.return_value = [0.1, 0.2, 0.3]
    mock_st_instance.encode.return_value = mock_embedding
    mock_sentence_transformer.return_value = mock_st_instance

    await llm_client.initialize()

    result = await llm_client.embed_text("Test text")
    assert result == [0.1, 0.2, 0.3]

    # We can't easily assert run_in_executor was called without mocking the loop,
    # but we can check if encode was called.
    # Note: Since it runs in a separate thread, depending on how MagicMock works with threads,
    # this might be flaky if we don't wait?
    # run_in_executor awaits the completion, so it should be fine.
    mock_st_instance.encode.assert_called_with("Test text")

@pytest.mark.asyncio
async def test_embed_text_failure(llm_client, mock_sentence_transformer):
    mock_st_instance = mock_sentence_transformer.return_value
    mock_st_instance.encode.side_effect = Exception("Encoding error")

    await llm_client.initialize()

    with pytest.raises(Exception, match="Encoding error"):
        await llm_client.embed_text("Test text")

@pytest.mark.asyncio
async def test_embed_text_uninitialized(llm_client):
    with pytest.raises(RuntimeError, match="Embedding model not initialized"):
        await llm_client.embed_text("Test text")

@pytest.mark.asyncio
async def test_embed_query(llm_client):
    # Should just call embed_text
    with patch.object(llm_client, "embed_text", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.1, 0.2]
        result = await llm_client.embed_query("query")
        assert result == [0.1, 0.2]
        mock_embed.assert_called_once_with("query")

@pytest.mark.asyncio
async def test_analyze_image_url(llm_client, mock_groq):
    mock_groq_instance = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Image description"))]
    mock_groq_instance.chat.completions.create.return_value = mock_response
    mock_groq.return_value = mock_groq_instance

    await llm_client.initialize()

    result = await llm_client.analyze_image(image_url="http://example.com/image.jpg")
    assert result == "Image description"

    call_kwargs = mock_groq_instance.chat.completions.create.call_args.kwargs
    content = call_kwargs["messages"][0]["content"]
    # Content is a list of dicts
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"] == "http://example.com/image.jpg"

@pytest.mark.asyncio
async def test_analyze_image_data(llm_client, mock_groq):
    mock_groq_instance = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Image description"))]
    mock_groq_instance.chat.completions.create.return_value = mock_response
    mock_groq.return_value = mock_groq_instance

    await llm_client.initialize()

    image_bytes = b"fake_image_data"
    result = await llm_client.analyze_image(image_data=image_bytes)
    assert result == "Image description"

    call_kwargs = mock_groq_instance.chat.completions.create.call_args.kwargs
    content = call_kwargs["messages"][0]["content"]
    assert content[1]["type"] == "image_url"
    expected_b64 = base64.b64encode(image_bytes).decode("utf-8")
    assert content[1]["image_url"]["url"] == f"data:image/jpeg;base64,{expected_b64}"

@pytest.mark.asyncio
async def test_analyze_image_no_input(llm_client, mock_groq):
    mock_groq_instance = AsyncMock()
    mock_groq.return_value = mock_groq_instance
    await llm_client.initialize()

    result = await llm_client.analyze_image()
    # It catches ValueError and returns error message
    assert "I could not analyze the image due to an error" in result
    assert "Either image_url or image_data must be provided" in result

@pytest.mark.asyncio
async def test_generate_text_with_all_options(llm_client, mock_groq):
    mock_groq_instance = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Generated text"))]
    mock_groq_instance.chat.completions.create.return_value = mock_response
    mock_groq.return_value = mock_groq_instance

    await llm_client.initialize()

    result = await llm_client.generate_text(
        prompt="Test prompt",
        system_prompt="Test system",
        temperature=0.5,
        max_tokens=50
    )
    assert result == "Generated text"

    mock_groq_instance.chat.completions.create.assert_called_once()
    call_kwargs = mock_groq_instance.chat.completions.create.call_args.kwargs
    assert call_kwargs["messages"] == [
        {"role": "system", "content": "Test system"},
        {"role": "user", "content": "Test prompt"}
    ]
    assert call_kwargs["model"] == "test_model"
    assert call_kwargs["temperature"] == 0.5
    assert call_kwargs["max_tokens"] == 50

@pytest.mark.asyncio
async def test_generate_text_api_failure(llm_client, mock_groq):
    mock_groq_instance = AsyncMock()
    mock_groq_instance.chat.completions.create.side_effect = Exception("API Error")
    mock_groq.return_value = mock_groq_instance

    await llm_client.initialize()

    with pytest.raises(Exception, match="API Error"):
        await llm_client.generate_text("Test prompt")

@pytest.mark.asyncio
async def test_generate_text_empty_response(llm_client, mock_groq):
    mock_groq_instance = AsyncMock()
    mock_response = MagicMock()
    # Mock content as None to simulate empty response if that happens
    mock_response.choices = [MagicMock(message=MagicMock(content=None))]
    mock_groq_instance.chat.completions.create.return_value = mock_response
    mock_groq.return_value = mock_groq_instance

    await llm_client.initialize()

    result = await llm_client.generate_text("Test prompt")
    assert result == ""
