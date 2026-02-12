"""
TTS Node - Converts text response to speech audio.
Uses configured TTS provider (ElevenLabs or Piper).
"""

import logging

from app.graph.state import TutorState
from app.services.tts_service import get_global_tts

logger = logging.getLogger(__name__)


async def tts_node(state: TutorState) -> TutorState:
    """
    Generate audio from text response.

    Args:
        state: Current tutor state

    Returns:
        Updated state with audio data
    """
    try:
        logger.debug("=== TTS NODE START ===")
        logger.debug(
            "TTS node processing",
            extra={
                "user_id": state["user_id"],
                "session_id": state["session_id"],
                "should_tts": state.get("should_tts", False),
                "response_length": len(state.get("response_text", "")),
            },
        )

        # Check if TTS is needed
        if not state.get("should_tts", False):
            logger.debug("TTS disabled for this response, skipping")
            state["audio_data"] = None
            return state

        response_text = state.get("response_text", "")

        if not response_text or response_text.strip() == "":
            logger.warning("Empty response text, skipping TTS")
            state["audio_data"] = None
            return state

        logger.debug("Getting TTS service...")

        tts_service = await get_global_tts()

        logger.debug(
            "Synthesizing speech...",
            extra={"text_length": len(response_text), "text_preview": response_text[:100]},
        )

        # Synthesize
        audio_data = await tts_service.synthesize(response_text)

        state["audio_data"] = audio_data

        logger.info(
            "TTS synthesis completed",
            extra={
                "text_length": len(response_text),
                "audio_size": len(audio_data) if audio_data else 0,
                "has_audio": audio_data is not None and len(audio_data) > 0,
            },
        )

        logger.debug("=== TTS NODE END ===")

        return state

    except Exception as e:
        logger.error(
            "TTS node failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "user_id": state.get("user_id"),
            },
            exc_info=True,
        )

        # Continue without audio
        state["audio_data"] = None
        state["error"] = f"TTS error: {str(e)}"

        return state


logger.debug("TTS node module loaded")
