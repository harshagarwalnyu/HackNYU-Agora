"""
Socrates Node - Main Socratic tutoring logic.
Generates questions, analogies, and guidance without giving direct answers.
"""

import logging

from app.config import settings
from app.graph.state import (
    MemorySummary,
    TutorState,
    VisualAction,
    VisualExtractionResult,
    get_conversation_context,
)
from app.services.llm_client import llm_client
from app.logging_config import log_exception

logger = logging.getLogger(__name__)


SOCRATIC_SYSTEM_PROMPT = """You are Agora, a world-class Socratic tutor. Your goal is to help students learn by guiding them to answers, not by giving answers directly. You are warm, encouraging, and patient.

CORE PRINCIPLES:
1.  **NEVER Give a Direct Answer:** Do not provide the final answer or a direct explanation unless the student's frustration is high (level 3+) AND they ask for it directly.
2.  **Guide with Questions:** Your primary tool is the guiding question. Ask questions that make the student think, recall, or connect concepts.
3.  **Use Analogies:** If a student is stuck, offer a simple analogy (like the sock one, but better) to re-frame the problem.
4.  **Use RAG & Web Context:** You will be given notes. They may come from student files OR web search.
    -   **Rule:** TRUST the context provided, especially if it helps clarify acronyms (e.g., "MCP" might mean "Model Context Protocol", not just "Microsoft").
    -   **Acronym Handling:** If the student uses an acronym (like "MCP") and the context suggests a specific meaning, adopt that meaning. If the context is ambiguous, ASK the student to clarify before guessing. "By 'MCP', do you mean Model Context Protocol, Microsoft Certified Professional, or something else?"
    -   **Example:** "I see from the search results that 'MCP' refers to [Concept]. How do you think this relates to..."

STUDENT INTERACTION RULES:
1.  **If the student asks "what is in my PDF?" (Generic Query):**
    -   The RAG context will contain a general summary.
    -   Your first response should be to *provide that summary* and then *ask a guiding question*.
    -   *Example:* "I've scanned your document! It looks like a deep dive into the PageRank algorithm, covering its use in search engines and its mathematical foundations. To get us started, what's your current understanding of what PageRank tries to solve?"

2.  **If the student says "I don't know" or "idk":**
    -   **Escalation Path:**
        1.  **First time:** Re-frame the question. Make it simpler. "No problem! Let's try looking at it this way: ..."
        2.  **Second time:** Offer a simple, relevant analogy. "Okay, let's try an analogy. Imagine website links are like 'votes'..."
        3.  **Third time:** Provide a small piece of information (a definition or hint) and immediately ask a follow-up question. "Okay, let's start with a key piece. PageRank is an algorithm that assigns a numerical weight to each page. Based on that, what do you think makes a page have a *high* weight?"

3.  **If student frustration is high (frustration_level >= 3):**
    -   Drop the Socratic method and become a *direct explainer*.
    -   Acknowledge their frustration and provide the clear, simple explanation they need.
    -   *Example:* "You're right, this is tricky and my questions might not be helping. Let's just walk through it. PageRank is..."

RESPONSE FORMAT:
-   Keep responses conversational and concise (2-4 sentences).
-   You may optionally create ONE sticky note visual aid.
-   [VISUAL: CREATE_NOTE | text: "A short hint or key term." | x: 100 | y: 200]
"""


def build_socratic_prompt(state: TutorState) -> str:
    """
    Build the full prompt for Socratic response generation.

    Args:
        state: Current tutor state

    Returns:
        Complete prompt string
    """
    logger.debug("Building Socratic prompt")

    # Conversation context
    context = get_conversation_context(state, max_turns=5)

    # RAG context
    rag_text = (
        "\n".join(
            f"[Note {idx}] {ctx['text']}"
            for idx, ctx in enumerate(state["rag_context"][: settings.rag_context_limit], 1)
        )
        if state["rag_context"]
        else ""
    )

    # Memory context
    memory_text = _format_memory_context(state.get("memory_summary"))

    # Frustration context
    frustration_note = ""
    if state["frustration_level"] >= settings.frustration_threshold:
        frustration_note = f"\n⚠️ FRUSTRATION LEVEL HIGH ({state['frustration_level']}/5): Provide more direct guidance."

    # Build full prompt
    prompt = f"""CONTEXT:
{context}

STUDENT'S CURRENT INPUT: {state["last_user_text"]}

RELEVANT NOTES:
{rag_text if rag_text else "No specific notes retrieved."}

STUDENT KNOWLEDGE:
{memory_text if memory_text else "No historical data yet."}

ROUTING: {state["routing"].value if state["routing"] else "unknown"}
MODE: {state["mode"].value}
{frustration_note}

Generate your Socratic response:"""

    logger.debug(
        "Socratic prompt built",
        extra={
            "prompt_length": len(prompt),
            "has_rag": bool(rag_text),
            "has_memory": bool(memory_text),
            "frustration_level": state["frustration_level"],
        },
    )

    return prompt


def extract_visual_actions(response_text: str) -> VisualExtractionResult:
    """
    Extract visual action commands from response text.

    Args:
        response_text: Generated response

    Returns:
        VisualExtractionResult with cleaned_text and actions list
    """
    import re

    visual_actions: list[VisualAction] = []
    cleaned_text = response_text

    # Find all [VISUAL: ...] patterns
    pattern = (
        r'\[VISUAL:\s*CREATE_NOTE\s*\|\s*text:\s*"([^"]+)"\s*\|\s*x:\s*(\d+)\s*\|\s*y:\s*(\d+)\]'
    )
    matches = re.finditer(pattern, response_text)

    for match in matches:
        text = match.group(1)
        x = int(match.group(2))
        y = int(match.group(3))

        visual_action: VisualAction = {
            "action": "CREATE_NOTE",
            "payload": {"text": text, "x": x, "y": y},
        }
        visual_actions.append(visual_action)

        logger.debug(
            "Visual action extracted",
            extra={"action": "CREATE_NOTE", "text_preview": text[:50], "position": (x, y)},
        )

    # Remove visual commands from text
    cleaned_text = re.sub(pattern, "", cleaned_text).strip()

    return {"cleaned_text": cleaned_text, "actions": visual_actions}


async def socrates_node(state: TutorState) -> TutorState:
    """
    Generate Socratic response using LLM.

    Args:
        state: Current tutor state

    Returns:
        Updated state with response
    """
    try:
        logger.debug("=== SOCRATES NODE START ===")
        logger.debug(
            "Socrates node processing",
            extra={
                "user_id": state["user_id"],
                "session_id": state["session_id"],
                "routing": state.get("routing"),
                "mode": state["mode"],
                "frustration_level": state["frustration_level"],
            },
        )

        # Build prompt
        prompt = build_socratic_prompt(state)

        logger.debug("Calling LLM for Socratic response...")

        # Generate response
        response = await llm_client.generate_text(
            prompt=prompt,
            system_prompt=SOCRATIC_SYSTEM_PROMPT,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

        logger.debug("Gemini response generated", extra={"response_length": len(response)})

        # Extract visual actions
        result = extract_visual_actions(response)
        state["response_text"] = result["cleaned_text"]
        state["visual_actions"] = result["actions"]
        state["should_tts"] = True

        logger.info(
            "Socratic response generated",
            extra={
                "response_length": len(result["cleaned_text"]),
                "visual_actions_count": len(result["actions"]),
                "frustration_level": state["frustration_level"],
            },
        )

        # Log response preview
        logger.debug("Response preview", extra={"preview": result["cleaned_text"][:200]})

        logger.debug("=== SOCRATES NODE END ===")

        return state

    except Exception as e:
        log_exception(logger, "Socrates node failed", e, {"user_id": state.get("user_id")})

        # Fallback response
        state["response_text"] = (
            "I'm having trouble processing that. Could you rephrase your question?"
        )
        state["visual_actions"] = []
        state["should_tts"] = True
        state["error"] = f"Socrates error: {str(e)}"

        return state


def _format_memory_context(memory: MemorySummary | None) -> str:
    """Format memory summary for prompt injection.

    Args:
        memory: Memory summary dict with 'mastered' and 'confused' keys

    Returns:
        Formatted string for prompt embedding
    """
    if not memory:
        return ""

    parts = []
    if memory.get("mastered"):
        parts.append(f"Student has mastered: {', '.join(memory['mastered'])}")
    if memory.get("confused"):
        parts.append(f"Student struggles with: {', '.join(memory['confused'])}")

    return "\n".join(parts) + ("\n" if parts else "")


logger.debug("Socrates node module loaded")
