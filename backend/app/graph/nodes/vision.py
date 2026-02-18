"""
Vision Node - Analyzes uploaded images using Multimodal LLMs.
Injects visual context into the conversation state.
"""

import logging
from app.graph.state import TutorState
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


async def vision_node(state: TutorState) -> TutorState:
    """
    Process any image data in the state using Groq Vision.

    Args:
        state: Current tutor state

    Returns:
        Updated state with image context
    """
    try:
        logger.debug("=== VISION NODE START ===")

        image_data = state.get("image_data")

        if not image_data:
            logger.debug("No image data found, skipping vision processing")
            return state

        logger.info("Processing image data...", extra={"user_id": state["user_id"]})

        # Determine specific prompt based on user text, or default
        user_text = state.get("last_user_text", "")
        prompt = (
            "Describe this image in detail, focusing on educational content, diagrams, or text."
        )

        if user_text:
            prompt = f"The user asked: '{user_text}'. Analyze the image to help answer this. Describe relevant details."

        description = await llm_client.analyze_image(image_url=image_data, prompt=prompt)

        state["image_context"] = description

        logger.info("Image analysis complete", extra={"description_length": len(description)})
        logger.debug(f"Image Context: {description[:100]}...")

        logger.debug("=== VISION NODE END ===")
        return state

    except Exception as e:
        logger.error("Vision node failed", exc_info=True)
        state["error"] = f"Vision error: {str(e)}"
        return state
