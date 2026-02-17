"""
RAG Node - Retrieves relevant context from student notes.
Uses embeddings and Qdrant vector search.
"""

import asyncio
import logging
import asyncio

from app.graph.state import RAGContext, RoutingDecision, TutorState
from app.services.llm_client import llm_client
from app.services.qdrant_client import qdrant_service

logger = logging.getLogger(__name__)


def _perform_web_search(query_text: str) -> list[dict]:
    """
    Perform synchronous web search using DuckDuckGo.
    This function is intended to be run in a separate thread.
    """
    from duckduckgo_search import DDGS

    web_results = []
    with DDGS() as ddgs:
        # Search for top 3 results
        results = list(ddgs.text(query_text, max_results=3))

        for res in results:
            web_results.append({
                "text": f"[WEB SOURCE: {res['title']}] {res['body']}",
                "score": 0.9, # Assign high confidence to fresh web results
                "metadata": {"source": "web_search", "url": res["href"]}
            })
    return web_results


async def rag_node(state: TutorState) -> TutorState:
    """
    Retrieve relevant notes/materials based on user query.

    Args:
        state: Current tutor state

    Returns:
        Updated state with RAG context
    """
    try:
        logger.debug("=== RAG NODE START ===")
        logger.debug(
            "RAG node processing",
            extra={
                "user_id": state["user_id"],
                "session_id": state["session_id"],
                "routing": state.get("routing"),
                "course_id": state.get("course_id"),
            },
        )

        # Only retrieve for NEW_QUESTION or QUIZ_ME
        routing = state.get("routing")
        if routing not in [RoutingDecision.NEW_QUESTION, RoutingDecision.QUIZ_ME]:
            logger.debug(
                "Skipping RAG - routing doesn't require retrieval", extra={"routing": routing}
            )
            state["rag_context"] = []
            return state

        query_text = state["last_user_text"]

        # Normalize the query to check for generic "what's in my doc" questions
        normalized_query = query_text.lower().strip().replace("?", "").replace(".", "")
        generic_queries = [
            "what is in that pdf",
            "what is in my pdf",
            "what are my notes about",
            "tell me about my document",
            "what is this pdf about",
            "so what is in that pdf you tell me",
            "give me an idea first",
        ]

        # Check if the normalized query is one of the generic phrases
        is_generic_query = any(q in normalized_query for q in generic_queries)

        if is_generic_query:
            logger.debug(
                "Generic meta-query detected. Using a broad query to fetch content.",
                extra={"original_query": query_text},
            )
            # Use a query that is semantically rich and represents "all content"
            query_text = "A general summary of all topics, concepts, and content in the document."

        if not query_text or query_text.strip() == "":
            logger.warning("Empty query text, skipping RAG")
            state["rag_context"] = []
            return state

        logger.debug("Generating query embedding", extra={"query_length": len(query_text)})

        # Generate query embedding
        query_embedding = await llm_client.embed_query(query_text)

        logger.debug("Query embedding generated", extra={"embedding_dim": len(query_embedding)})

        # Search Qdrant
        logger.debug("Searching Qdrant for relevant notes...")

        search_results = await qdrant_service.search_notes(
            query_embedding=query_embedding,
            user_id=state["user_id"],
            course_id=state.get("course_id"),
            limit=5,
        )

        # Fallback: Web Search if results are poor
        top_score = search_results[0]["score"] if search_results else 0.0
        
        if top_score < 0.5:
            logger.info(
                f"Low RAG score ({top_score:.2f}). Initiating Web Search via DuckDuckGo...",
                extra={"query": query_text},
            )

            try:
                # Run the blocking search in a separate thread
                web_results = await asyncio.to_thread(_perform_web_search, query_text)
                
                if web_results:
                    logger.info(f"Found {len(web_results)} web results")
                    # Append web results to search results
                    search_results.extend(web_results)
                else:
                    logger.warning("Web search returned no results")
                    
            except Exception as e:
                logger.error(f"Async web search execution failed: {e}", exc_info=True)
                # Fallback mock if DDG execution fails completely
                web_results = [
                    {
                        "text": f"[WEB SEARCH FAILED] Could not retrieve external information for '{query_text}'.",
                        "score": 0.1,
                        "metadata": {"source": "system_error", "url": "#"}
                    }
                ]
                search_results.extend(web_results)

        logger.info(
            "RAG search completed",
            extra={"results_count": len(search_results), "query_preview": query_text[:50]},
        )

        # Format results
        rag_context: list[RAGContext] = []
        for result in search_results:
            ctx: RAGContext = {
                "text": result["text"],
                "score": result["score"],
                "metadata": result.get("metadata", {}),
            }
            rag_context.append(ctx)

            logger.debug(
                "Retrieved context",
                extra={"text_preview": result["text"][:100], "score": result["score"]},
            )

        state["rag_context"] = rag_context
        state["rag_query"] = query_text

        # Log retrieval quality
        if rag_context:
            top_score = rag_context[0]["score"]
            logger.info(
                "RAG retrieval quality",
                extra={
                    "top_score": top_score,
                    "results_count": len(rag_context),
                    "quality": "high"
                    if top_score > 0.7
                    else "medium"
                    if top_score > 0.5
                    else "low",
                },
            )
        else:
            logger.warning(
                "No relevant notes found",
                extra={"query": query_text[:50], "user_id": state["user_id"]},
            )

        logger.debug("=== RAG NODE END ===")

        return state

    except Exception as e:
        logger.error(
            "RAG node failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "user_id": state.get("user_id"),
                "session_id": state.get("session_id"),
            },
            exc_info=True,
        )

        # Continue without RAG context
        state["rag_context"] = []
        state["error"] = f"RAG error: {str(e)}"

        return state


logger.debug("RAG node module loaded")
