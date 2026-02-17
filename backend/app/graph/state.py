"""
TutorState definition for LangGraph.
Represents the complete state of a tutoring session.
"""

import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict

logger = logging.getLogger(__name__)


class TutorMode(str, Enum):
    """Tutoring modes."""

    SOCRATIC = "socratic"
    QUIZ = "quiz"
    EXPLAIN = "explain"
    VISUAL = "visual"


class RoutingDecision(str, Enum):
    """Routing classifications."""

    NEW_QUESTION = "new_question"
    ANSWER_TO_MY_QUESTION = "answer_to_my_question"
    FRUSTRATED_INTERRUPTION = "frustrated_interruption"
    REQUEST_FOR_VISUAL = "request_for_visual"
    QUIZ_ME = "quiz_me"


class VisualAction(TypedDict):
    """Visual action for whiteboard."""

    action: str  # CREATE_NOTE, LOAD_IMAGE, HIGHLIGHT_REGION
    payload: Dict[str, Any]


class Message(TypedDict):
    """Conversation message."""

    role: str  # student, tutor
    content: str
    timestamp: float


class RAGContext(TypedDict):
    """Retrieved context from notes."""

    text: str
    score: float
    metadata: Dict[str, Any]


class MemorySummary(TypedDict):
    """Student memory/understanding summary."""

    mastered: List[str]
    confused: List[str]
    last_updated: float


class TutorState(TypedDict):
    """
    Complete state for the Agora tutor LangGraph.

    This state flows through all nodes and accumulates context.
    """

    # Session identifiers
    user_id: str
    session_id: str
    course_id: Optional[str]

    # Conversation history
    messages: List[Message]

    # Current turn
    last_user_text: str
    last_audio_format: Optional[str]
    image_data: Optional[str]  # URL or base64
    image_context: Optional[str]  # Description of the image

    # Mode & routing
    mode: TutorMode
    routing: Optional[RoutingDecision]

    # RAG context
    rag_context: List[RAGContext]
    rag_query: Optional[str]

    # Memory
    memory_summary: Optional[MemorySummary]
    turn_count: int

    # Frustration tracking
    frustration_level: int
    consecutive_same_questions: int

    # Response generation
    response_text: str
    visual_actions: List[VisualAction]
    should_tts: bool
    audio_data: Optional[bytes]

    # Metadata
    error: Optional[str]
    processing_time: float


def create_initial_state(
    user_id: str, session_id: str, course_id: Optional[str] = None
) -> TutorState:
    """
    Create initial tutor state for a new session.

    Args:
        user_id: User identifier
        session_id: Session identifier
        course_id: Optional course identifier

    Returns:
        Initial TutorState
    """
    logger.debug(
        "Creating initial state",
        extra={"user_id": user_id, "session_id": session_id, "course_id": course_id},
    )

    state: TutorState = {
        "user_id": user_id,
        "session_id": session_id,
        "course_id": course_id,
        "messages": [],
        "last_user_text": "",
        "last_audio_format": None,
        "image_data": None,
        "image_context": None,
        "mode": TutorMode.SOCRATIC,
        "routing": None,
        "rag_context": [],
        "rag_query": None,
        "memory_summary": None,
        "turn_count": 0,
        "frustration_level": 0,
        "consecutive_same_questions": 0,
        "response_text": "",
        "visual_actions": [],
        "should_tts": True,
        "audio_data": None,
        "error": None,
        "processing_time": 0.0,
    }

    logger.info(
        "Initial state created",
        extra={"user_id": user_id, "session_id": session_id, "mode": state["mode"]},
    )

    return state


def add_message(state: TutorState, role: str, content: str) -> TutorState:
    """
    Add a message to the conversation history.

    Args:
        state: Current state
        role: Message role (student/tutor)
        content: Message content

    Returns:
        Updated state
    """
    message: Message = {"role": role, "content": content, "timestamp": time.time()}

    state["messages"].append(message)

    logger.debug(
        "Message added to state",
        extra={
            "role": role,
            "content_length": len(content),
            "total_messages": len(state["messages"]),
        },
    )

    return state


def get_conversation_context(state: TutorState, max_turns: int = 10) -> str:
    """
    Get formatted conversation context for prompts.

    Args:
        state: Current state
        max_turns: Maximum number of recent turns to include

    Returns:
        Formatted conversation string
    """
    recent_messages = state["messages"][-max_turns * 2 :] if max_turns else state["messages"]

    context_lines = []
    for msg in recent_messages:
        role = "Student" if msg["role"] == "student" else "Tutor"
        context_lines.append(f"{role}: {msg['content']}")

    context = "\n".join(context_lines)

    logger.debug(
        "Conversation context extracted",
        extra={
            "total_messages": len(state["messages"]),
            "included_messages": len(recent_messages),
            "context_length": len(context),
        },
    )

    return context


logger.debug("TutorState module loaded")
