"""
Reflector Node - Metacognition layer.
Critiques and improves the tutor's response before sending it to the user.
"""

import logging
from app.graph.state import TutorState
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)

REFLECTION_PROMPT = """You are a Senior Educational Supervisor.
Review the Tutor's response to the Student.

Student Query: "{user_text}"
Tutor Response: "{response_text}"

Critique this response based on:
1. Accuracy: Is it factually correct?
2. Pedagogy: Is it Socratic? Does it guide rather than just give the answer?
3. Clarity: Is it simple and easy to understand?

If the response is good (Score > 8/10), return "GOOD".
If it needs improvement, REWRITE it to be better.

Return ONLY the rewritten response, or the word "GOOD".
"""


async def reflector_node(state: TutorState) -> TutorState:
    """
    Review and potentially rewrite the tutor's response.

    Args:
        state: Current tutor state

    Returns:
        Updated state with potentially improved response
    """
    try:
        logger.debug("=== REFLECTOR NODE START ===")

        response_text = state.get("response_text", "")
        if not response_text:
            return state

        user_text = state.get("last_user_text", "")

        # lightweight check - maybe skip for very short responses
        if len(response_text) < 20:
            return state

        logger.debug("Reflecting on response...", extra={"original_length": len(response_text)})

        prompt = REFLECTION_PROMPT.format(user_text=user_text, response_text=response_text)

        critique = await llm_client.generate_text(
            prompt=prompt,
            temperature=0.3,  # Low temp for critical evaluation
            max_tokens=1024,
        )

        if critique.strip().upper() == "GOOD":
            logger.info("Reflection passed: Response is good.")
        else:
            logger.info("Reflection active: Rewriting response.")
            state["response_text"] = critique.strip()

        logger.debug("=== REFLECTOR NODE END ===")
        return state

    except Exception:
        logger.error("Reflector node failed", exc_info=True)
        # On error, just keep original response
        return state
