"""
FastAPI application entry point for Agora backend.
Initializes services, routes, and WebSocket connections.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import socketio

from app.config import settings
from app.logging_config import setup_logging

# Setup logging first
setup_logging(log_level=settings.log_level, log_file=settings.log_file)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    logger.info("=" * 80)
    logger.info("Starting Agora Backend Application")
    logger.info("=" * 80)
    logger.debug(
        "Lifespan startup initiated",
        extra={
            "app_name": settings.app_name,
            "version": settings.app_version,
            "debug_mode": settings.debug,
        },
    )

    # Initialize services
    try:
        logger.debug("Initializing Qdrant client...")
        from app.services.qdrant_client import qdrant_service

        await qdrant_service.initialize()
        logger.info("Qdrant client initialized successfully")

        logger.debug("Initializing LLM client...")
        from app.services.llm_client import llm_client

        await llm_client.initialize()
        logger.info("LLM client initialized successfully (Groq)")

        logger.debug("Initializing STT service...")
        from app.services.stt_service import get_stt_service

        stt = get_stt_service()
        await stt.initialize()
        logger.info(f"STT service initialized: {settings.stt_provider}")

        logger.debug("Initializing TTS service...")
        from app.services.tts_service import get_tts_service

        tts = get_tts_service()
        await tts.initialize()
        logger.info(f"TTS service initialized: {settings.tts_provider}")

        logger.info("All services initialized successfully")
        logger.info("Application ready to accept requests")

    except Exception as e:
        logger.critical(
            "Failed to initialize services",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise

    yield

    # Shutdown
    logger.info("=" * 80)
    logger.info("Shutting down Agora Backend Application")
    logger.info("=" * 80)
    logger.debug("Lifespan shutdown initiated")

    try:
        logger.debug("Closing Qdrant client...")
        await qdrant_service.close()
        logger.info("Qdrant client closed")

        logger.debug("Closing LLM client...")
        await llm_client.close()
        logger.info("LLM client closed")

        logger.info("Shutdown completed successfully")

    except Exception as e:
        logger.error(
            "Error during shutdown",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Voice-first Socratic tutor with multimodal RAG",
    lifespan=lifespan,
    debug=settings.debug,
)

logger.debug(
    "FastAPI app created", extra={"title": settings.app_name, "version": settings.app_version}
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.debug("CORS middleware configured")


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify service status.
    """
    logger.debug("Health check requested")

    health_status = {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "services": {},
    }

    # Check Qdrant
    try:
        from app.services.qdrant_client import qdrant_service

        qdrant_health = await qdrant_service.health_check()
        health_status["services"]["qdrant"] = "healthy" if qdrant_health else "unhealthy"
        logger.debug(f"Qdrant health: {health_status['services']['qdrant']}")
    except Exception as e:
        health_status["services"]["qdrant"] = f"error: {str(e)}"
        logger.warning("Qdrant health check failed", extra={"error": str(e)})

    # Check LLM (Groq)
    try:
        from app.services.llm_client import llm_client

        llm_health = await llm_client.health_check()
        health_status["services"]["llm"] = "healthy" if llm_health else "unhealthy"
        logger.debug(f"LLM health: {health_status['services']['llm']}")
    except Exception as e:
        health_status["services"]["llm"] = f"error: {str(e)}"
        logger.warning("LLM health check failed", extra={"error": str(e)})

    logger.info("Health check completed", extra=health_status)

    return JSONResponse(content=health_status)


@app.get("/")
async def root():
    """Root endpoint."""
    logger.debug("Root endpoint accessed")
    return {"message": "Agora Backend API", "version": settings.app_version, "docs": "/docs"}


@app.get("/api/progress")
async def get_user_progress():
    """Get the user's knowledge graph/progress."""
    try:
        from pathlib import Path
        import json
        
        kg_path = Path("backend/storage/user_knowledge_graph.json")
        if kg_path.exists():
            with open(kg_path, "r") as f:
                data = json.load(f)
            return data
        else:
            return []
    except Exception:
        logger.error("Failed to fetch progress", exc_info=True)
        return []

# Import and include routers
logger.debug("Importing route modules...")

try:
    from app.api import materials, ws

    app.include_router(materials.router, prefix="/api/materials", tags=["materials"])
    logger.debug("Materials router registered: /api/materials")

    logger.info("All routers registered successfully")

    # Wrap FastAPI app with Socket.IO (Must be last)
    app = socketio.ASGIApp(ws.sio, app)

except Exception as e:
    logger.error(
        "Failed to register routers",
        extra={"error": str(e), "error_type": type(e).__name__},
        exc_info=True,
    )


if __name__ == "__main__":
    import uvicorn

    logger.info(
        "Starting uvicorn server",
        extra={"host": settings.host, "port": settings.port, "reload": settings.reload},
    )

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
