"""
Memory Node - Manages student understanding tracking.
Loads historical memory and updates based on interactions.
"""

import logging
import time

from typing import cast
from app.config import settings
from app.graph.state import MemorySummary, TutorState, get_conversation_context
from app.services.llm_client import llm_client
from app.services.qdrant_client import qdrant_service

logger = logging.getLogger(__name__)


MEMORY_ANALYSIS_PROMPT = """You are analyzing a tutoring conversation to understand what the student has mastered vs what they're confused about.

Analyze the recent conversation and identify:
1. Topics the student clearly understands (mastered)
2. Topics the student is struggling with or confused about
3. A quantitative "Knowledge Graph" update: Key concepts discussed and a mastery score (0-100) based on their performance.

Respond with ONLY valid JSON in this format:
{
  "mastered": ["topic1", "topic2"],
  "confused": ["topic3", "topic4"],
  "knowledge_graph": [
    {"concept": "Recursion", "score": 85, "status": "mastered"},
    {"concept": "Pointers", "score": 40, "status": "struggling"}
  ]
}

Be specific. Extract actual topic names."""


async def load_memory_node(state: TutorState) -> TutorState:
    """
    Load historical memory summaries for the student.

    Args:
        state: Current tutor state

    Returns:
        Updated state with memory summary
    """
    try:
        logger.debug("=== LOAD MEMORY NODE START ===")
        logger.debug(
            "Loading memory", extra={"user_id": state["user_id"], "session_id": state["session_id"]}
        )

        # Retrieve memories from Qdrant
        memories = await qdrant_service.get_memory(user_id=state["user_id"], limit=5)

        logger.debug("Memories retrieved", extra={"memories_count": len(memories)})

        if not memories:
            logger.info(
                "No historical memory found, initializing empty",
                extra={"user_id": state["user_id"]},
            )
            state["memory_summary"] = {"mastered": [], "confused": [], "last_updated": time.time()}
            return state

        # Aggregate memories
        all_mastered = []
        all_confused = []

        for memory in memories:
            memory_data = memory.get("memory_data", {})
            all_mastered.extend(memory_data.get("mastered", []))
            all_confused.extend(memory_data.get("confused", []))

        # Deduplicate
        all_mastered = list(set(all_mastered))
        all_confused = list(set(all_confused))

        # Remove items from confused if they're now mastered
        all_confused = [topic for topic in all_confused if topic not in all_mastered]

        logger.info(
            "Memory loaded and aggregated",
            extra={
                "mastered_count": len(all_mastered),
                "confused_count": len(all_confused),
                "memories_processed": len(memories),
            },
        )

        state["memory_summary"] = {
            "mastered": all_mastered,
            "confused": all_confused,
            "last_updated": time.time(),
        }

        logger.debug("=== LOAD MEMORY NODE END ===")

        return state

    except Exception as e:
        logger.error(
            "Load memory node failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "user_id": state.get("user_id"),
            },
            exc_info=True,
        )

        # Initialize empty memory
        state["memory_summary"] = {"mastered": [], "confused": [], "last_updated": time.time()}
        state["error"] = f"Memory load error: {str(e)}"

        return state


async def update_memory_node(state: TutorState) -> TutorState:
    """
    Update memory based on recent conversation.
    Called periodically (every N turns).

    Args:
        state: Current tutor state

    Returns:
        Updated state with refreshed memory
    """
    try:
        logger.debug("=== UPDATE MEMORY NODE START ===")
        logger.debug(
            "Updating memory",
            extra={
                "user_id": state["user_id"],
                "session_id": state["session_id"],
                "turn_count": state["turn_count"],
            },
        )

        # Check if update is needed
        update_interval = settings.memory_update_interval
        if state["turn_count"] % update_interval != 0:
            logger.debug(
                "Skipping memory update - not at interval",
                extra={"turn_count": state["turn_count"], "interval": update_interval},
            )
            return state

        # Get recent conversation
        context = get_conversation_context(state, max_turns=update_interval)

        if not context or context.strip() == "":
            logger.warning("Empty conversation context, skipping memory update")
            return state

        logger.debug(
            "Analyzing conversation for memory update",
            extra={
                "context_length": len(context),
                "turns_analyzed": min(update_interval * 2, len(state["messages"])),
            },
        )

        # Analyze with LLM
        prompt = f"""Recent Conversation:
{context}

Analyze this conversation:"""

        logger.debug("Calling LLM for memory analysis...")

        memory_json = await llm_client.generate_json(
            prompt=prompt, system_prompt=MEMORY_ANALYSIS_PROMPT
        )

        logger.debug(
            "Memory analysis completed",
            extra={
                "mastered_count": len(memory_json.get("mastered", [])),
                "confused_count": len(memory_json.get("confused", [])),
            },
        )

        # Merge with existing memory
        current_memory = state.get("memory_summary") or {
            "mastered": [],
            "confused": [],
            "last_updated": 0.0,
        }

        new_mastered = list(set(current_memory["mastered"] + memory_json.get("mastered", [])))
        new_confused = list(set(current_memory["confused"] + memory_json.get("confused", [])))

        # Remove confused topics that are now mastered
        new_confused = [topic for topic in new_confused if topic not in new_mastered]

        updated_memory = {
            "mastered": new_mastered,
            "confused": new_confused,
            "last_updated": time.time(),
        }

        state["memory_summary"] = cast(MemorySummary, updated_memory)

        # Save Knowledge Graph to JSON file for Frontend Dashboard
        try:
            import json
            from pathlib import Path

            kg_path = Path("backend/storage/user_knowledge_graph.json")
            existing_kg = []
            if kg_path.exists():
                with open(kg_path, "r") as f:
                    existing_kg = json.load(f)

            # Merge new KG updates
            new_concepts = memory_json.get("knowledge_graph", [])

            # Simple merge strategy: update if exists, append if new
            kg_dict = {item["concept"]: item for item in existing_kg}
            for item in new_concepts:
                kg_dict[item["concept"]] = item

            final_kg = list(kg_dict.values())

            with open(kg_path, "w") as f:
                json.dump(final_kg, f, indent=2)

            logger.info("Knowledge Graph saved", extra={"concepts_count": len(final_kg)})

        except Exception:
            logger.error("Failed to save Knowledge Graph", exc_info=True)

        logger.info(
            "Memory updated successfully",
            extra={
                "mastered_count": len(new_mastered),
                "confused_count": len(new_confused),
                "new_mastered": memory_json.get("mastered", []),
                "new_confused": memory_json.get("confused", []),
            },
        )

        # Generate embedding and store in Qdrant
        memory_text = f"Mastered: {', '.join(new_mastered)}. Confused: {', '.join(new_confused)}."

        logger.debug("Embedding and storing memory in Qdrant...")

        embedding = await llm_client.embed_text(memory_text)

        await qdrant_service.upsert_memory(
            user_id=state["user_id"],
            session_id=state["session_id"],
            memory_data=updated_memory,
            embedding=embedding,
        )

        logger.info(
            "Memory persisted to Qdrant",
            extra={"user_id": state["user_id"], "session_id": state["session_id"]},
        )

        logger.debug("=== UPDATE MEMORY NODE END ===")

        return state

    except Exception as e:
        logger.error(
            "Update memory node failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "user_id": state.get("user_id"),
            },
            exc_info=True,
        )

        state["error"] = f"Memory update error: {str(e)}"

        return state


logger.debug("Memory node module loaded")
