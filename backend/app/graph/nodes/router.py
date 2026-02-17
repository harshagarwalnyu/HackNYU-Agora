"""
Router Node - Classifies user input and determines processing path.
Uses Gemini to analyze intent and route appropriately.
"""

import logging

from app.graph.state import RoutingDecision, TutorState, get_conversation_context
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


ROUTER_SYSTEM_PROMPT = """You are a routing classifier for an AI tutor system.

Analyze the student's input and classify it into ONE of these categories:

1. NEW_QUESTION: Student asks a new question about the material
2. ANSWER_TO_MY_QUESTION: Student provides an answer or explanation in response to tutor's question
3. FRUSTRATED_INTERRUPTION: Student expresses frustration, confusion, or asks for direct answers
4. REQUEST_FOR_VISUAL: Student explicitly asks for a diagram, visual, or whiteboard
5. QUIZ_ME: Student requests to be quizzed or tested

Consider the conversation context. If the tutor just asked a question, the student is likely providing ANSWER_TO_MY_QUESTION.

Respond with ONLY the category name, nothing else."""


async def router_node(state: TutorState) -> TutorState:
    """
    Route user input to appropriate processing path.

    Args:
        state: Current tutor state

    Returns:
        Updated state with routing decision
    """
    try:
        logger.debug("=== ROUTER NODE START ===")
        logger.debug(
            "Router node processing",
            extra={
                "user_id": state["user_id"],
                "session_id": state["session_id"],
                "last_user_text": state["last_user_text"][:100],
                "turn_count": state["turn_count"],
            },
        )

        user_input = state["last_user_text"]

        if not user_input or user_input.strip() == "":
            logger.warning("Empty user input, defaulting to NEW_QUESTION")
            state["routing"] = RoutingDecision.NEW_QUESTION
            return state

        # Get conversation context
        context = get_conversation_context(state, max_turns=3)

        logger.debug(
            "Building classification prompt",
            extra={"context_length": len(context), "input_length": len(user_input)},
        )

        # Build classification prompt
        prompt = f"""Conversation Context:
{context}

Student's Latest Input: {user_input}

Classification:"""

        logger.debug("Calling LLM for routing classification...")

        # Call LLM
        classification = await llm_client.generate_text(
            prompt=prompt, system_prompt=ROUTER_SYSTEM_PROMPT, temperature=0.3, max_tokens=50
        )

        classification = classification.strip().upper()

        logger.debug("Raw classification result", extra={"classification": classification})

        # Parse classification
        routing = None
        if "NEW_QUESTION" in classification:
            routing = RoutingDecision.NEW_QUESTION
        elif "ANSWER_TO_MY_QUESTION" in classification:
            routing = RoutingDecision.ANSWER_TO_MY_QUESTION
        elif "FRUSTRATED" in classification or "FRUSTRATION" in classification:
            routing = RoutingDecision.FRUSTRATED_INTERRUPTION
            state["frustration_level"] = min(state["frustration_level"] + 1, 5)
            logger.info(
                "Frustration detected", extra={"frustration_level": state["frustration_level"]}
            )
        elif "VISUAL" in classification or "REQUEST_FOR_VISUAL" in classification:
            routing = RoutingDecision.REQUEST_FOR_VISUAL
        elif "QUIZ" in classification:
            routing = RoutingDecision.QUIZ_ME
        else:
            logger.warning(f"Unknown classification: {classification}, defaulting to NEW_QUESTION")
            routing = RoutingDecision.NEW_QUESTION

        state["routing"] = routing

        logger.info(
            "Routing decision made",
            extra={
                "routing": routing.value,
                "user_input_preview": user_input[:50],
                "frustration_level": state["frustration_level"],
            },
        )

        logger.debug("=== ROUTER NODE END ===")

        return state

    except Exception as e:
        logger.error(
            "Router node failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "user_id": state.get("user_id"),
                "session_id": state.get("session_id"),
            },
            exc_info=True,
        )

        # Fallback
        state["routing"] = RoutingDecision.NEW_QUESTION
        state["error"] = f"Router error: {str(e)}"

        return state


logger.debug("Router node module loaded")
