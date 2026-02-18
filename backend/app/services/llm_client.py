"""
SOTA LLM Client (Groq Free Tier).
Handles interactions with Groq's high-performance API (Llama 3 / Mixtral).
"""

import logging
import json
import asyncio
from functools import partial
from typing import Any, Dict, List, Optional, cast

from groq import AsyncGroq
from groq.types.chat import ChatCompletionMessageParam
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with Groq LLM API and Local Embeddings."""

    def __init__(self) -> None:
        """Initialize LLM client."""
        self.api_key = settings.groq_api_key
        self.model_name = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens

        self.client: Optional[AsyncGroq] = None
        self.embedding_model: Optional[SentenceTransformer] = None

        logger.info(
            "LLMClient instantiated",
            extra={"model": self.model_name, "api_key": self.api_key},
        )

    async def initialize(self) -> None:
        """Initialize the Groq client and local embedding model."""
        try:
            # Check for placeholder key
            if self.api_key == "your_groq_api_key_here" or not self.api_key:
                logger.warning(
                    "Empty or placeholder GROQ_API_KEY detected. AI features will fail until a valid key is provided in .env."
                )

            logger.debug("Initializing Groq client...")
            self.client = AsyncGroq(api_key=self.api_key)

            logger.debug("Loading local embedding model: all-MiniLM-L6-v2...")
            # Run on separate thread to prevent blocking event loop during model load
            loop = asyncio.get_running_loop()
            self.embedding_model = await loop.run_in_executor(
                None, partial(SentenceTransformer, "all-MiniLM-L6-v2")
            )

            logger.info("LLM client initialized successfully (Groq + SentenceTransformer)")

        except Exception as e:
            logger.error("Failed to initialize LLM client", extra={"error": str(e)}, exc_info=True)
            raise

    async def close(self) -> None:
        """Close the client."""
        logger.debug("Closing LLM client...")
        if self.client:
            await self.client.close()
        self.client = None
        self.embedding_model = None
        logger.info("LLM client closed")

    async def health_check(self) -> bool:
        """Check if Groq API is accessible."""
        try:
            if not self.client:
                return False

            # Simple generation test
            await self.client.chat.completions.create(
                messages=[{"role": "user", "content": "ping"}], model=self.model_name, max_tokens=1
            )
            return True

        except Exception as e:
            logger.error(f"LLM health check failed: {str(e)}", exc_info=True)
            return False

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate text using Groq."""
        try:
            if not self.client:
                raise RuntimeError("LLM client not initialized")

            messages: List[ChatCompletionMessageParam] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            # Check for specific Groq authentication errors
            error_msg = str(e)
            if "AuthenticationError" in type(e).__name__ or "401" in error_msg:
                friendly_msg = "Invalid or missing Groq API Key. Please check your .env file and ensure GROQ_API_KEY is set correctly."
                logger.error(friendly_msg, extra={"error": error_msg})
                # We return it as a string instead of raising so the graph can handle it or the user sees it
                return f"Error: {friendly_msg}"

            logger.error("Text generation failed", exc_info=True)
            raise

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate JSON using Groq."""
        try:
            # Enforce JSON mode via system prompt
            json_instruction = (
                "\nIMPORTANT: You must respond with valid JSON only. No markdown, no explanations."
            )
            full_system = (system_prompt or "") + json_instruction

            response_text = await self.generate_text(
                prompt=prompt,
                system_prompt=full_system,
                temperature=0.001,  # Extremely low temp for consistent JSON
            )

            # Clean up potential markdown blocks
            clean_text = response_text.replace("```json", "").replace("```", "").strip()

            return cast(Dict[str, Any], json.loads(clean_text))

        except Exception:
            logger.error("JSON generation failed", exc_info=True)
            raise

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate batch local embeddings."""
        try:
            if not self.embedding_model:
                raise RuntimeError("Embedding model not initialized")

            if not texts:
                return []

            # Run on a separate thread to prevent blocking the event loop
            loop = asyncio.get_running_loop()
            embeddings = await loop.run_in_executor(
                None, partial(self.embedding_model.encode, texts)
            )
            return cast(List[List[float]], embeddings.tolist())

        except Exception:
            logger.error("Batch embedding generation failed", exc_info=True)
            raise

    async def embed_text(self, text: str) -> List[float]:
        """Generate local embeddings."""
        try:
            if not self.embedding_model:
                raise RuntimeError("Embedding model not initialized")

            # Run on a separate thread to prevent blocking the event loop
            # SentenceTransformer.encode is CPU-bound but releases GIL, so threading is effective
            loop = asyncio.get_running_loop()
            embedding = await loop.run_in_executor(None, partial(self.embedding_model.encode, text))
            return cast(List[float], embedding.tolist())

        except Exception:
            logger.error("Embedding generation failed", exc_info=True)
            raise

    async def embed_query(self, query: str) -> List[float]:
        """Generate query embedding."""
        return await self.embed_text(query)

    async def analyze_image(
        self,
        image_url: Optional[str] = None,
        image_data: Optional[bytes] = None,
        mime_type: str = "image/jpeg",
        prompt: str = "Describe this image in detail.",
    ) -> str:
        """
        Analyze an image using Groq's Vision model.

        Args:
            image_url: URL of the image
            image_data: Raw image bytes
            mime_type: MIME type of the image (if providing data)
            prompt: Question or instruction for the vision model

        Returns:
            Description or answer based on the image
        """
        try:
            if not self.client:
                raise RuntimeError("LLM client not initialized")

            logger.debug(
                "Calling Groq Vision API...", extra={"model": "llama-3.2-90b-vision-preview"}
            )

            # Prepare image content
            img_content: Dict[str, Any] = {"type": "image_url", "image_url": {}}

            if image_url:
                img_content["image_url"]["url"] = image_url
            elif image_data:
                import base64

                b64_data = base64.b64encode(image_data).decode("utf-8")
                data_url = f"data:{mime_type};base64,{b64_data}"
                img_content["image_url"]["url"] = data_url
            else:
                raise ValueError("Either image_url or image_data must be provided")

            response = await self.client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                messages=cast(
                    List[ChatCompletionMessageParam],
                    [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                img_content,
                            ],
                        }
                    ],
                ),
                temperature=0.5,
                max_tokens=1024,
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            logger.error("Image analysis failed", exc_info=True)
            return f"I could not analyze the image due to an error: {str(e)}"


# Global singleton
llm_client = LLMClient()
