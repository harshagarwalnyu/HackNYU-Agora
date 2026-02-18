from unittest.mock import AsyncMock, patch
import pytest

from app.graph.state import RoutingDecision
from app.graph.nodes.rag import rag_node

@pytest.mark.asyncio
@patch("app.graph.nodes.rag.llm_client")
@patch("app.graph.nodes.rag.qdrant_service")
async def test_rag_node_low_score_fallback(mock_qdrant_service, mock_llm_client):
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

    mock_llm_client.embed_query = AsyncMock(return_value=[0.1] * 768)
    mock_qdrant_service.search_notes = AsyncMock(return_value=mock_search_results)

    # patch search_duckduckgo
    with patch("app.graph.nodes.rag.search_duckduckgo", new_callable=AsyncMock) as mock_search:
        # Mock to return a list of results
        mock_search.return_value = [
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
@patch("app.graph.nodes.rag.llm_client")
@patch("app.graph.nodes.rag.qdrant_service")
async def test_rag_node_generic_query(mock_qdrant_service, mock_llm_client):
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

    mock_llm_client.embed_query = AsyncMock(return_value=[0.1] * 768)
    mock_qdrant_service.search_notes = AsyncMock(return_value=mock_search_results)

    # We want to verify that embed_query was called with the summarized query, not the original
    expected_query = "A general summary of all topics, concepts, and content in the document."

    await rag_node(state)

    mock_llm_client.embed_query.assert_called_with(expected_query)
