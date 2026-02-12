"""
Speech-to-Text (STT) service using Groq Whisper.
Extremely fast, free tier available.
"""

import logging
import io
from abc import ABC, abstractmethod
from typing import Optional

from groq import AsyncGroq
from app.config import settings

logger = logging.getLogger(__name__)


class STTEngine(ABC):
    """Abstract base class for STT engines."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the STT engine."""
        pass

    @abstractmethod
    async def transcribe(self, audio_data: bytes, format: str = "webm") -> str:
        """Transcribe audio to text."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close and cleanup resources."""
        pass


class GroqWhisperSTT(STTEngine):
    """Groq API / Whisper implementation."""

    def __init__(self):
        """Initialize Groq Whisper STT."""
        self.api_key = settings.groq_api_key
        self.model = settings.stt_model
        self.client: Optional[AsyncGroq] = None

        logger.debug("GroqWhisperSTT instantiated", extra={"model": self.model})

    async def initialize(self) -> None:
        """Initialize Groq client."""
        try:
            logger.debug("Initializing Groq client for STT...")
            self.client = AsyncGroq(api_key=self.api_key)
            logger.info("Groq STT initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize Groq STT", extra={"error": str(e)}, exc_info=True)
            raise

    async def transcribe(self, audio_data: bytes, format: str = "webm") -> str:
        """
        Transcribe audio using Groq Whisper.

        Args:
            audio_data: Raw audio bytes
            format: Audio format (webm, wav, etc.)
        """
        try:
            logger.debug(
                "Transcribing with Groq Whisper",
                extra={"audio_size": len(audio_data), "format": format},
            )

            if not self.client:
                raise RuntimeError("Groq client not initialized")

            # Groq API expects a file-like object with a name
            # We wrap bytes in BytesIO and give it a name
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{format}"

            transcription = await self.client.audio.transcriptions.create(
                file=(audio_file.name, audio_data),
                model=self.model,
                response_format="text",
                language="en",
            )

            # Groq returns raw text string when response_format="text"
            text = str(transcription)

            logger.info("Groq transcription completed", extra={"transcript_length": len(text)})

            return text.strip()

        except Exception as e:
            logger.error("Groq transcription failed", extra={"error": str(e)}, exc_info=True)
            raise

    async def close(self) -> None:
        """Close Groq client."""
        logger.debug("Closing Groq client...")
        if self.client:
            await self.client.close()
        self.client = None
        logger.info("Groq client closed")


# Factory function
def get_stt_service() -> STTEngine:
    """Get the configured STT service."""
    # We only support Groq Whisper now for SOTA Free Tier
    return GroqWhisperSTT()


# Global singleton
_stt_service: Optional[STTEngine] = None
_stt_initialized: bool = False


async def get_global_stt() -> STTEngine:
    """Get or create global STT service instance."""
    global _stt_service, _stt_initialized

    if _stt_service is None:
        _stt_service = get_stt_service()

    if not _stt_initialized:
        await _stt_service.initialize()
        _stt_initialized = True

    return _stt_service
