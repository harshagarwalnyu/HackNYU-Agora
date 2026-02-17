import sys
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

# Mock heavy dependencies BEFORE importing module under test
sys.modules["groq"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["qdrant_client"] = MagicMock()
# We also mock the service modules to avoid their imports
sys.modules["app.services.llm_client"] = MagicMock()
sys.modules["app.services.qdrant_client"] = MagicMock()

# Now import the things we need
# app.graph.state is lightweight, we can import it or mock it.
# It is better to use real state definitions if possible, but let's see.
# Assuming app.graph.state has no heavy deps.
try:
    from app.graph.state import TutorState, RoutingDecision
except ImportError:
    # If it fails (e.g. typing extensions issue), we mock it too
    RoutingDecision = MagicMock()
    RoutingDecision.NEW_QUESTION = "new_question"
    TutorState = dict

from app.graph.nodes.rag import rag_node

@pytest.mark.asyncio
async def test_rag_node_low_score_fallback():
    # Setup initial state
    state = {
        "user_id": "test_user",
        "session_id": "test_session",
        "routing": RoutingDecision.NEW_QUESTION,
        "last_user_text": "What is Python?",
        "rag_context": [],
        "course_id": "test_course"
    }

    # Mock qdrant search results with low score
    mock_search_results = [{"score": 0.3, "text": "Something irrelevant", "metadata": {}}]

    # Configure the mocked services that rag_node imported
    # rag_node imported llm_client from app.services.llm_client
    # So we need to access that imported object in rag module

    # Actually, since we mocked sys.modules["app.services.llm_client"],
    # the 'llm_client' imported in rag_node is sys.modules["app.services.llm_client"].llm_client

    mock_llm_client = sys.modules["app.services.llm_client"].llm_client
    mock_llm_client.embed_query = AsyncMock(return_value=[0.1] * 768)

    mock_qdrant_service = sys.modules["app.services.qdrant_client"].qdrant_service
    mock_qdrant_service.search_notes = AsyncMock(return_value=mock_search_results)

    # patch DDGS
    with patch("duckduckgo_search.DDGS") as mock_ddgs_cls:

        # Mock DDGS context manager and text search
        mock_ddgs_instance = MagicMock()
        mock_ddgs_cls.return_value.__enter__.return_value = mock_ddgs_instance

        # Mock the text() method to return a list of results
        mock_ddgs_instance.text.return_value = [
            {"title": "Python", "body": "Python is a language", "href": "http://python.org"}
        ]

        # Run function
        new_state = await rag_node(state)

        # Verify
        rag_context = new_state["rag_context"]
        # Should have 2 results: 1 from Qdrant, 1 from DDG
        assert len(rag_context) == 2

        # Check the DDG result (should be the second one)
        ddg_result = rag_context[1]
        assert "[WEB SOURCE: Python]" in ddg_result["text"]
        assert ddg_result["score"] == 0.9
        assert ddg_result["metadata"]["source"] == "web_search"
        assert ddg_result["metadata"]["url"] == "http://python.org"

@pytest.mark.asyncio
async def test_rag_node_generic_query():
    state = {
        "user_id": "test_user",
        "session_id": "test_session",
        "routing": RoutingDecision.NEW_QUESTION,
        "last_user_text": "tell me about my document",
        "rag_context": [],
        "course_id": "test_course"
    }

    # Mock qdrant search results
    mock_search_results = [{"score": 0.8, "text": "Some notes", "metadata": {}}]

    mock_llm_client = sys.modules["app.services.llm_client"].llm_client
    mock_llm_client.embed_query = AsyncMock(return_value=[0.1] * 768)

    mock_qdrant_service = sys.modules["app.services.qdrant_client"].qdrant_service
    mock_qdrant_service.search_notes = AsyncMock(return_value=mock_search_results)

    # We want to verify that embed_query was called with the summarized query, not the original
    expected_query = "A general summary of all topics, concepts, and content in the document."

    await rag_node(state)

    mock_llm_client.embed_query.assert_called_with(expected_query)
