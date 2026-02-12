"""
LangGraph Builder - Constructs the tutor state graph.
Connects all nodes with conditional edges.
"""

import logging
import time
from typing import cast, Any

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from app.graph.state import RoutingDecision, TutorState, add_message
from app.graph.nodes.router import router_node
from app.graph.nodes.rag import rag_node
from app.graph.nodes.memory import load_memory_node, update_memory_node
from app.graph.nodes.socrates import socrates_node
from app.graph.nodes.quiz import quiz_node
from app.graph.nodes.tts_node import tts_node
from app.graph.nodes.vision import vision_node
from app.graph.nodes.reflector import reflector_node

logger = logging.getLogger(__name__)


from typing import cast, Any, Callable, Awaitable

# Node wrapper to add timing and message tracking
def create_timed_node(node_func: Callable[[TutorState], Awaitable[TutorState]], node_name: str) -> Callable[[TutorState], Awaitable[TutorState]]:
    """
    Wrap a node function with timing and logging.
    
    Args:
        node_func: Node function to wrap
        node_name: Name for logging
        
    Returns:
        Wrapped function
    """

    async def wrapped(state: TutorState) -> TutorState:
        start_time = time.time()
        logger.info(
            f"Node started: {node_name}",
            extra={
                "node": node_name,
                "user_id": state.get("user_id"),
                "session_id": state.get("session_id"),
            },
        )

        result = await node_func(state)

        elapsed = time.time() - start_time
        result["processing_time"] += elapsed

        logger.info(
            f"Node completed: {node_name}",
            extra={
                "node": node_name,
                "elapsed_ms": int(elapsed * 1000),
                "total_processing_ms": int(result["processing_time"] * 1000),
            },
        )

        return result

    return wrapped


def routing_decision(state: TutorState) -> str:
    """
    Determine which processing node to route to based on classification.

    Args:
        state: Current state

    Returns:
        Next node name
    """
    routing = state.get("routing")

    logger.debug(
        "Routing decision",
        extra={"routing": routing.value if routing else "none", "mode": state.get("mode")},
    )

    if routing == RoutingDecision.QUIZ_ME:
        return "quiz"
    else:
        # All other routes go to socrates for now
        return "socrates"


def build_tutor_graph() -> Any:
    """
    Build and compile the tutor state graph.

    Returns:
        Compiled StateGraph
    """
    logger.debug("Building tutor graph...")

    # Create graph
    workflow = StateGraph(TutorState)

    logger.debug("Adding nodes to graph...")

    # Add nodes with timing
    workflow.add_node("load_memory", cast(Any, create_timed_node(load_memory_node, "load_memory")))
    workflow.add_node("vision", cast(Any, create_timed_node(vision_node, "vision")))
    workflow.add_node("router", cast(Any, create_timed_node(router_node, "router")))
    workflow.add_node("rag", cast(Any, create_timed_node(rag_node, "rag")))
    workflow.add_node("socrates", cast(Any, create_timed_node(socrates_node, "socrates")))
    workflow.add_node("quiz", cast(Any, create_timed_node(quiz_node, "quiz")))
    workflow.add_node("reflector", cast(Any, create_timed_node(reflector_node, "reflector")))
    workflow.add_node("update_memory", cast(Any, create_timed_node(update_memory_node, "update_memory")))
    workflow.add_node("tts", cast(Any, create_timed_node(tts_node, "tts")))

    logger.debug("Nodes added: load_memory, vision, router, rag, socrates, quiz, reflector, update_memory, tts")

    # Define edges
    logger.debug("Defining graph edges...")

    # Start with loading memory
    workflow.set_entry_point("load_memory")

    # Memory → Vision (Process any images)
    workflow.add_edge("load_memory", "vision")
    
    # Vision → Router
    workflow.add_edge("vision", "router")

    # Router → RAG (always retrieve context)
    workflow.add_edge("router", "rag")

    # RAG → Conditional (socrates or quiz)
    workflow.add_conditional_edges(
        "rag", routing_decision, {"socrates": "socrates", "quiz": "quiz"}
    )

    # Both socrates and quiz → Reflector (Metacognition)
    workflow.add_edge("socrates", "reflector")
    workflow.add_edge("quiz", "reflector")
    
    # Reflector → Update Memory
    workflow.add_edge("reflector", "update_memory")

    # Update memory → TTS
    workflow.add_edge("update_memory", "tts")

    # TTS → END
    workflow.add_edge("tts", END)

    logger.debug("Graph edges defined")

    # Compile
    logger.debug("Compiling graph...")
    graph = workflow.compile()

    logger.info(
        "Tutor graph compiled successfully",
        extra={
            "nodes": ["load_memory", "router", "rag", "socrates", "quiz", "update_memory", "tts"],
            "edges_count": 7,
        },
    )

    return graph


# Global graph instance
_tutor_graph: Any | None = None


def get_tutor_graph() -> Any:
    """
    Get or create the global tutor graph instance.

    Returns:
        Compiled tutor graph
    """
    global _tutor_graph

    if _tutor_graph is None:
        logger.debug("Creating tutor graph instance...")
        _tutor_graph = build_tutor_graph()
        logger.info("Global tutor graph created")

    return _tutor_graph


async def process_user_input(
    state: TutorState, 
    user_text: str, 
    audio_format: str | None = None,
    image_data: str | None = None
) -> TutorState:
    """
    Process user input through the tutor graph.

    Args:
        state: Current tutor state
        user_text: Transcribed user text
        audio_format: Optional audio format
        image_data: Optional image data (URL or base64)

    Returns:
        Updated state after processing
    """
    try:
        logger.info("=" * 80)
        logger.info("PROCESSING USER INPUT")
        logger.info("=" * 80)
        logger.debug(
            "Processing user input",
            extra={
                "user_id": state["user_id"],
                "session_id": state["session_id"],
                "input_length": len(user_text),
                "has_image": image_data is not None,
                "turn_count": state["turn_count"],
            },
        )

        # Update state with new input
        state["last_user_text"] = user_text
        state["last_audio_format"] = audio_format
        state["image_data"] = image_data
        state["image_context"] = None # Reset previous image context
        state["turn_count"] += 1
        state["processing_time"] = 0.0
        state["error"] = None

        # Add student message
        state = add_message(state, "student", user_text)

        logger.debug("State updated with user input", extra={"turn_count": state["turn_count"]})

        # Get graph
        graph = get_tutor_graph()

        logger.debug("Running graph...")

        # Run graph
        result = await graph.ainvoke(state)
        result = cast(TutorState, result)

        logger.debug("Graph execution completed")

        # Add tutor response message
        if result.get("response_text"):
            result = add_message(result, "tutor", result["response_text"])

        logger.info(
            "Input processing completed",
            extra={
                "turn_count": result["turn_count"],
                "processing_time_ms": int(result["processing_time"] * 1000),
                "response_length": len(result.get("response_text", "")),
                "has_audio": result.get("audio_data") is not None,
                "visual_actions_count": len(result.get("visual_actions", [])),
                "error": result.get("error"),
            },
        )

        logger.info("=" * 80)

        return result

    except Exception as e:
        logger.error(
            "Graph processing failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "user_id": state.get("user_id"),
                "session_id": state.get("session_id"),
            },
            exc_info=True,
        )

        # Return state with error
        state["error"] = f"Processing error: {str(e)}"
        state["response_text"] = "I encountered an error processing your input. Please try again."
        state["should_tts"] = False

        return state


logger.debug("Graph builder module loaded")
