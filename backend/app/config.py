"""
Configuration management for Agora backend using Pydantic Settings.
Loads environment variables and provides validated configuration.
"""

import logging
from pathlib import Path
from typing import Literal, Any, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application
    app_name: str = "Agora Backend"
    app_version: str = "0.2.0-SOTA"
    debug: bool = False
    log_level: str = "DEBUG"
    log_file: str | None = Field(default=None, description="Path to log file")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    backend_cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # API Keys
    groq_api_key: str = Field(alias="GROQ_API_KEY")

    # Qdrant Configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_notes: str = "agora_notes"
    qdrant_collection_memory: str = "agora_memory"
    qdrant_vector_size: int = 768  # Standard embedding dimension

    # LLM Configuration (Groq)
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama-3.3-70b-versatile"  # Reliable SOTA
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096

    # STT Settings (Groq Whisper)
    stt_provider: Literal["groq_whisper"] = "groq_whisper"
    stt_model: str = "whisper-large-v3"

    # TTS Settings (Edge-TTS)
    tts_provider: Literal["edge_tts"] = "edge_tts"
    tts_voice: str = "en-US-AriaNeural"  # High quality Microsoft voice

    # Storage
    storage_path: Path = Field(default=Path("backend/storage"))
    upload_max_size: int = 50 * 1024 * 1024  # 50MB

    # Session & Memory
    session_timeout: int = 3600  # 1 hour
    memory_update_interval: int = 5  # Update memory every N turns
    frustration_threshold: int = 3  # Frustration level to trigger mode change

    # Feature Flags
    enable_quiz_mode: bool = True
    enable_visual_actions: bool = True
    enable_frustration_monitor: bool = True
    enable_self_explanation: bool = False  # Advanced feature

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str] | str:
        """Parse CORS origins from a comma-separated string."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @field_validator("storage_path")
    @classmethod
    def create_storage_path(cls, v: Path) -> Path:
        """Ensure storage directory exists."""
        v.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Storage path validated: {v}")
        return v

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str] | str:
        """Parse CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        logger.debug(
            "Settings initialized",
            extra={
                "app_name": self.app_name,
                "debug": self.debug,
                "stt_provider": self.stt_provider,
                "tts_provider": self.tts_provider,
                "llm_base_url": self.llm_base_url,
                "llm_model": self.llm_model,
            },
        )


# Global settings instance
settings = Settings()

logger.info(
    "Configuration loaded successfully",
    extra={
        "config_source": ".env",
        "log_level": settings.log_level,
        "feature_flags": {
            "quiz_mode": settings.enable_quiz_mode,
            "visual_actions": settings.enable_visual_actions,
            "frustration_monitor": settings.enable_frustration_monitor,
        },
    },
)
