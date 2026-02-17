import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import os

# Set environment variables before imports to avoid validation errors
os.environ["GROQ_API_KEY"] = "dummy_key"

# Mock dependencies before importing the module under test
import sys
sys.modules["groq"] = MagicMock()
sys.modules["groq.types"] = MagicMock()
sys.modules["groq.types.chat"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()

# Now import the module under test
from app.services.llm_client import LLMClient

@pytest.fixture
def mock_groq_client():
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock()
    return mock_client

@pytest.fixture
def llm_client(mock_groq_client):
    # Initialize the client but replace the internal client with our mock
    client = LLMClient()
    client.client = mock_groq_client
    return client

@pytest.mark.asyncio
async def test_generate_text_success(llm_client, mock_groq_client):
    """Test successful text generation."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Hello world"))]
    mock_groq_client.chat.completions.create.return_value = mock_response

    response = await llm_client.generate_text("Hi")

    assert response == "Hello world"
    mock_groq_client.chat.completions.create.assert_called_once()
    call_args = mock_groq_client.chat.completions.create.call_args
    assert call_args.kwargs["messages"] == [{"role": "user", "content": "Hi"}]

@pytest.mark.asyncio
async def test_generate_text_with_system_prompt(llm_client, mock_groq_client):
    """Test text generation with a system prompt."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Hello world"))]
    mock_groq_client.chat.completions.create.return_value = mock_response

    await llm_client.generate_text("Hi", system_prompt="You are a helpful assistant")

    call_args = mock_groq_client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    assert len(messages) == 2
    assert messages[0] == {"role": "system", "content": "You are a helpful assistant"}
    assert messages[1] == {"role": "user", "content": "Hi"}

@pytest.mark.asyncio
async def test_generate_text_parameters(llm_client, mock_groq_client):
    """Test text generation with custom parameters."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Hello world"))]
    mock_groq_client.chat.completions.create.return_value = mock_response

    await llm_client.generate_text("Hi", temperature=0.5, max_tokens=100)

    call_args = mock_groq_client.chat.completions.create.call_args
    assert call_args.kwargs["temperature"] == 0.5
    assert call_args.kwargs["max_tokens"] == 100

@pytest.mark.asyncio
async def test_generate_text_uninitialized(llm_client):
    """Test text generation when client is not initialized."""
    llm_client.client = None
    with pytest.raises(RuntimeError, match="LLM client not initialized"):
        await llm_client.generate_text("Hi")

@pytest.mark.asyncio
async def test_generate_text_api_error(llm_client, mock_groq_client):
    """Test text generation when API call fails."""
    mock_groq_client.chat.completions.create.side_effect = Exception("API Error")

    with pytest.raises(Exception, match="API Error"):
        await llm_client.generate_text("Hi")
