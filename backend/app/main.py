"""
FastAPI application entry point for Agora backend.
Initializes services, routes, and WebSocket connections.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import socketio

from app.config import settings
from app.logging_config import setup_logging
from app.services.qdrant_client import qdrant_service
from app.services.llm_client import llm_client
from app.services.stt_service import get_stt_service
from app.services.tts_service import get_tts_service

# Setup logging first
setup_logging(log_level=settings.log_level, log_file=settings.log_file)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
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
        await qdrant_service.initialize()
        logger.info("Qdrant client initialized successfully")

        logger.debug("Initializing LLM client...")
        await llm_client.initialize()
        logger.info("LLM client initialized successfully (Groq)")

        logger.debug("Initializing STT service...")
        stt = get_stt_service()
        await stt.initialize()
        logger.info(f"STT service initialized: {settings.stt_provider}")

        logger.debug("Initializing TTS service...")
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


# Rate Limiter setup
limiter = Limiter(key_func=get_remote_address)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to every response.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' ws: wss:;"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Voice-first Socratic tutor with multimodal RAG",
    lifespan=lifespan,
    debug=settings.debug,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

logger.debug(
    "FastAPI app created", extra={"title": settings.app_name, "version": settings.app_version}
)

# GZip compression first (outermost) to minimize payload size
app.add_middleware(GZipMiddleware, minimum_size=1000)
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.debug("CORS middleware configured")


@app.get("/health")
@limiter.limit("100/15minutes")
async def health_check(request: Request) -> JSONResponse:
    """
    Health check endpoint to verify service status.
    """
    logger.debug("Health check requested")
    # Short cache so load balancers get fresh status without hammering the server
    headers = {"Cache-Control": "public, max-age=10"}

    health_status: dict[str, Any] = {
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

    return JSONResponse(content=health_status, headers=headers)


@app.get("/")
@limiter.limit("100/15minutes")
async def root(request: Request) -> dict[str, str]:
    """Root endpoint."""
    logger.debug("Root endpoint accessed")
    return {"message": "Agora Backend API", "version": settings.app_version, "docs": "/docs"}


@app.get("/api/progress")
@limiter.limit("50/15minutes")
async def get_user_progress(request: Request) -> Any:
    """Get the user's knowledge graph/progress. Read-heavy; cache 1 hour."""
    try:
        from pathlib import Path
        import json
        import aiofiles

        kg_path = Path("backend/storage/user_knowledge_graph.json")
        if kg_path.exists():
            async with aiofiles.open(kg_path, mode="r") as f:
                content = await f.read()
                data = json.loads(content)
            return JSONResponse(
                content=data,
                headers={"Cache-Control": "public, max-age=3600"},
            )
        else:
            return JSONResponse(
                content=[],
                headers={"Cache-Control": "public, max-age=3600"},
            )
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
