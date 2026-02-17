"""
Quiz Node - Generates quiz questions based on memory and notes.
Uses confused topics and retrieved materials to create practice questions.
"""

import logging

from app.graph.state import TutorState, VisualAction
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


QUIZ_SYSTEM_PROMPT = """You are generating a quiz question for a student.

RULES:
1. Create ONE clear, focused question
2. Base it on the topics the student struggles with (confused topics)
3. Use the provided notes as reference material
4. Make it challenging but fair
5. Use Socratic style - ask them to explain or apply concepts
6. DO NOT provide the answer

RESPONSE FORMAT:
Generate just the question. Be specific and clear.
You may optionally add a sticky note hint using:
[VISUAL: CREATE_NOTE | text: "hint text" | x: 100 | y: 200]
"""


async def quiz_node(state: TutorState) -> TutorState:
    """
    Generate a quiz question for the student.

    Args:
        state: Current tutor state

    Returns:
        Updated state with quiz question
    """
    try:
        logger.debug("=== QUIZ NODE START ===")
        logger.debug(
            "Quiz node processing",
            extra={"user_id": state["user_id"], "session_id": state["session_id"]},
        )

        # Get confused topics from memory
        memory = state.get("memory_summary")
        confused_topics = memory["confused"] if memory else []

        if not confused_topics:
            logger.warning("No confused topics found, using general quiz approach")
            confused_topics = ["the material"]

        logger.debug(
            "Quiz topics identified",
            extra={"confused_topics": confused_topics, "topics_count": len(confused_topics)},
        )

        # Get RAG context for reference
        rag_text = ""
        if state["rag_context"]:
            rag_chunks = []
            for idx, ctx in enumerate(state["rag_context"][:2], 1):
                rag_chunks.append(f"[Reference {idx}] {ctx['text']}")
            rag_text = "\n".join(rag_chunks)

        # Build quiz prompt
        prompt = f"""TOPICS TO QUIZ ON:
{", ".join(confused_topics)}

REFERENCE NOTES:
{rag_text if rag_text else "No specific notes available."}

STUDENT'S REQUEST: {state["last_user_text"]}

Generate a quiz question:"""

        logger.debug(
            "Quiz prompt built", extra={"prompt_length": len(prompt), "has_notes": bool(rag_text)}
        )

        logger.debug("Calling LLM for quiz generation...")

        # Generate quiz question
        quiz_response = await llm_client.generate_text(
            prompt=prompt,
            system_prompt=QUIZ_SYSTEM_PROMPT,
            temperature=0.8,  # Higher temperature for variety
        )

        logger.debug("Quiz question generated", extra={"response_length": len(quiz_response)})

        # Extract visual actions (hints)
        import re

        visual_actions: list[VisualAction] = []
        cleaned_response = quiz_response

        pattern = r'\[VISUAL:\s*CREATE_NOTE\s*\|\s*text:\s*"([^"]+)"\s*\|\s*x:\s*(\d+)\s*\|\s*y:\s*(\d+)\]'
        matches = re.finditer(pattern, quiz_response)

        for match in matches:
            text = match.group(1)
            x = int(match.group(2))
            y = int(match.group(3))

            visual_action: VisualAction = {
                "action": "CREATE_NOTE",
                "payload": {"text": text, "x": x, "y": y},
            }
            visual_actions.append(visual_action)

            logger.debug("Quiz hint created", extra={"hint_preview": text[:50]})

        cleaned_response = re.sub(pattern, "", cleaned_response).strip()

        state["response_text"] = cleaned_response
        state["visual_actions"] = visual_actions
        state["should_tts"] = True

        logger.info(
            "Quiz question generated",
            extra={
                "question_length": len(cleaned_response),
                "hints_count": len(visual_actions),
                "topics_quizzed": confused_topics,
            },
        )

        logger.debug("=== QUIZ NODE END ===")

        return state

    except Exception as e:
        logger.error(
            "Quiz node failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "user_id": state.get("user_id"),
            },
            exc_info=True,
        )

        # Fallback
        state["response_text"] = (
            "Let's start with a question: Can you explain the main concept we've been discussing?"
        )
        state["visual_actions"] = []
        state["should_tts"] = True
        state["error"] = f"Quiz error: {str(e)}"

        return state


logger.debug("Quiz node module loaded")
