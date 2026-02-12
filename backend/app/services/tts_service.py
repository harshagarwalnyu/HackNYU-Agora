"""
Text-to-Speech (TTS) service using Edge-TTS.
High quality, free, unlimited neural voices.
"""

import logging

from abc import ABC, abstractmethod
from typing import Optional

# We will use the edge_tts library
import edge_tts
from app.config import settings

logger = logging.getLogger(__name__)


class TTSEngine(ABC):
    """Abstract base class for TTS engines."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the TTS engine."""
        pass

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Synthesize speech from text."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close and cleanup resources."""
        pass


class EdgeTTS(TTSEngine):
    """Microsoft Edge TTS implementation."""

    def __init__(self):
        """Initialize Edge TTS."""
        self.voice = settings.tts_voice
        logger.debug("EdgeTTS instantiated", extra={"voice": self.voice})

    async def initialize(self) -> None:
        """Initialize Edge TTS (no-op, stateless)."""
        logger.info("Edge TTS initialized (stateless)")

    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize speech using Edge TTS.

        Args:
            text: Text to synthesize.

        Returns:
            Audio bytes (MP3).
        """
        try:
            logger.debug(
                "Synthesizing with Edge TTS", extra={"text_length": len(text), "voice": self.voice}
            )

            communicate = edge_tts.Communicate(text, self.voice)

            # Accumulate bytes in memory
            # The library typically wants to write to file, but we can iterate chunks
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            if not audio_data:
                raise RuntimeError("Edge TTS produced empty audio")

            logger.info("Edge TTS synthesis completed", extra={"audio_size": len(audio_data)})

            return audio_data

        except Exception as e:
            logger.error("Edge TTS synthesis failed", extra={"error": str(e)}, exc_info=True)
            raise

    async def close(self) -> None:
        """Close resources (no-op)."""
        pass


# Factory function
def get_tts_service() -> TTSEngine:
    """Get the configured TTS service."""
    # We only support Edge TTS now for SOTA Free Tier
    return EdgeTTS()


# Global singleton
_tts_service: Optional[TTSEngine] = None
_tts_initialized: bool = False


async def get_global_tts() -> TTSEngine:
    """Get or create global TTS service instance."""
    global _tts_service, _tts_initialized

    if _tts_service is None:
        _tts_service = get_tts_service()

    if not _tts_initialized:
        await _tts_service.initialize()
        _tts_initialized = True

    return _tts_service
