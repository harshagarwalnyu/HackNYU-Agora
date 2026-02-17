"""
WebSocket API for real-time voice interactions using Socket.IO.
Handles audio streaming, STT, LangGraph processing, and TTS responses.
"""

import logging
import base64
from typing import Dict, Any
import uuid
import asyncio

import socketio
from fastapi import APIRouter

from app.graph.state import create_initial_state, TutorState
from app.graph.builder import process_user_input
from app.services.stt_service import get_global_stt

logger = logging.getLogger(__name__)

router = APIRouter()

# Create Socket.IO server
# Note: python-socketio 5.x uses Engine.IO 5.x protocol
# Client must use socket.io-client 4.x or 5.x compatible version
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25,
)

# Active sessions mapped by socket ID
active_sessions: Dict[str, TutorState] = {}
# Active tasks mapped by socket ID for interruption
active_tasks: Dict[str, asyncio.Task[None]] = {}


@sio.event
async def connect(sid: str, environ: Dict[str, Any], auth: Dict[str, Any]) -> bool:
    """Handle client connection."""
    logger.info("=" * 80)
    logger.info("SOCKET.IO CONNECTION ESTABLISHED")
    logger.info("=" * 80)
    logger.info("Client connected", extra={"sid": sid, "query": environ.get("QUERY_STRING", "")})

    # Parse query params
    query_string = environ.get("QUERY_STRING", "")
    params = {}
    if query_string:
        for param in query_string.split("&"):
            if "=" in param:
                key, value = param.split("=", 1)
                params[key] = value

    user_id = params.get("user_id")
    session_id = params.get("session_id", str(uuid.uuid4()))

    logger.info(
        "Connection params", extra={"sid": sid, "user_id": user_id, "session_id": session_id}
    )

    # DON'T emit 'connect' - it's a reserved Socket.IO event
    # Client will receive the built-in 'connect' event automatically
    logger.info("Ready for messages", extra={"sid": sid})

    return True


@sio.event
async def disconnect(sid: str) -> None:
    """Handle client disconnection."""
    logger.info("Client disconnected", extra={"sid": sid})

    # Cleanup session
    if sid in active_sessions:
        del active_sessions[sid]
        logger.debug("Session cleaned up", extra={"sid": sid})

    logger.info("=" * 80)


@sio.event
async def interrupt(sid: str, data: Dict[str, Any]) -> None:
    """Handle interruption signal (stop generating/speaking)."""
    logger.info("Interruption signal received", extra={"sid": sid})
    
    if sid in active_tasks:
        task = active_tasks[sid]
        task.cancel()
        logger.info("Cancelled active task", extra={"sid": sid})
        # Wait a moment to ensure cleanup
        await asyncio.sleep(0.1)
        await sio.emit("session_status", {"status": "interrupted"}, to=sid)
    else:
        logger.debug("No active task to interrupt", extra={"sid": sid})


@sio.event
async def init_session(sid: str, data: Dict[str, Any]) -> None:
    """Initialize a new tutoring session."""
    try:
        logger.debug("Initializing session", extra={"sid": sid})

        user_id = data.get("user_id")
        session_id = data.get("session_id", str(uuid.uuid4()))
        course_id = data.get("course_id")

        if not user_id:
            logger.error("Missing user_id")
            await sio.emit("error", {"message": "user_id required"}, to=sid)
            return

        logger.debug(
            "Creating initial state",
            extra={"user_id": user_id, "session_id": session_id, "course_id": course_id},
        )

        # Create initial state
        state = create_initial_state(user_id=user_id, session_id=session_id, course_id=course_id)

        # Store session
        active_sessions[sid] = state

        logger.info(
            "Session initialized", extra={"sid": sid, "user_id": user_id, "session_id": session_id}
        )

        # Confirm
        await sio.emit(
            "session_initialized",
            {"session_id": session_id, "user_id": user_id, "course_id": course_id},
            to=sid,
        )

    except Exception as e:
        logger.error(
            "Session init failed",
            extra={"sid": sid, "error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )

        await sio.emit("error", {"message": f"Session init failed: {str(e)}"}, to=sid)


@sio.event
async def audio_input(sid: str, data: Dict[str, Any]) -> None:
    """Handle audio input message."""
    try:
        logger.debug("Processing audio_input message", extra={"sid": sid})

        # Get session
        if sid not in active_sessions:
            logger.error("No active session", extra={"sid": sid})
            await sio.emit(
                "error", {"message": "No active session. Send init_session first."}, to=sid
            )
            return

        state = active_sessions[sid]

        stt_service = await get_global_stt()

        # Extract audio data
        audio_format = data.get("format", "webm")
        audio_data_b64 = data.get("data")

        if not audio_data_b64:
            logger.error("No audio data")
            await sio.emit("error", {"message": "No audio data"}, to=sid)
            return

        # Decode base64
        logger.debug("Decoding audio data...")
        audio_bytes = base64.b64decode(audio_data_b64)

        logger.info(
            "Audio received",
            extra={"sid": sid, "audio_size": len(audio_bytes), "format": audio_format},
        )

        file_extension = "webm"  # Default
        if "/" in audio_format:
            # This will turn "audio/webm" into "webm"
            file_extension = audio_format.split("/")[-1]

        logger.debug(f"Parsed file extension: {file_extension}")

        # Transcribe
        logger.debug("Transcribing audio...")
        await sio.emit("session_status", {"message": "Transcribing..."}, to=sid)

        transcript = await stt_service.transcribe(audio_bytes, format=file_extension)

        logger.info(
            "Audio transcribed",
            extra={"sid": sid, "transcript": transcript, "transcript_length": len(transcript)},
        )

        # Send transcript back
        await sio.emit("transcript", {"from": "student", "text": transcript}, to=sid)

        # Process with graph (cancellable)
        task = asyncio.create_task(
            process_and_respond(
                sid=sid, state=state, user_text=transcript, audio_format=audio_format
            )
        )
        active_tasks[sid] = task
        
        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"Task cancelled for session {sid}")
            await sio.emit("session_status", {"status": "cancelled"}, to=sid)
        finally:
            active_tasks.pop(sid, None)

    except Exception as e:
        logger.error(
            "Audio message handling failed",
            extra={"sid": sid, "error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )

        await sio.emit(
            "error",
            {
                "message": f"Audio processing failed: {str(e)}",
                "error_type": type(e).__name__,
                "details": str(e),
            },
            to=sid,
        )


@sio.event
async def text_input(sid: str, data: Dict[str, Any]) -> None:
    """Handle text input message."""
    try:
        logger.debug("Processing text_input message", extra={"sid": sid})

        # Get session
        if sid not in active_sessions:
            logger.error("No active session")
            await sio.emit(
                "error", {"message": "No active session. Send init_session first."}, to=sid
            )
            return

        state = active_sessions[sid]

        text_content = data.get("text", "")

        if not text_content:
            logger.error("Empty text")
            return

        logger.info("Text message received", extra={"sid": sid, "text": text_content})

        # Process (cancellable)
        task = asyncio.create_task(
            process_and_respond(sid=sid, state=state, user_text=text_content, audio_format=None)
        )
        active_tasks[sid] = task
        
        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"Task cancelled for session {sid}")
            await sio.emit("session_status", {"status": "cancelled"}, to=sid)
        finally:
            active_tasks.pop(sid, None)

    except Exception as e:
        logger.error(
            "Text message handling failed",
            extra={"sid": sid, "error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )

        await sio.emit(
            "error",
            {
                "message": f"Text processing failed: {str(e)}",
                "error_type": type(e).__name__,
                "details": str(e),
            },
            to=sid,
        )


async def process_and_respond(
    sid: str, state: TutorState, user_text: str, audio_format: str | None
) -> None:
    """Process user input through LangGraph and send responses."""
    try:
        logger.debug(
            "Processing input through graph", extra={"sid": sid, "user_text_length": len(user_text)}
        )

        # Send thinking status
        await sio.emit("session_status", {"message": "Thinking..."}, to=sid)

        # Process through graph
        result_state = await process_user_input(
            state=state, user_text=user_text, audio_format=audio_format
        )

        # Update session state
        active_sessions[sid] = result_state

        logger.debug(
            "Graph processing completed",
            extra={"sid": sid, "processing_time_ms": int(result_state["processing_time"] * 1000)},
        )

        # Send tutor transcript with RAG context info
        if result_state.get("response_text"):
            rag_context_count = len(result_state.get("rag_context", []))
            rag_sources_used = rag_context_count > 0

            await sio.emit(
                "transcript",
                {
                    "from": "tutor",
                    "text": result_state["response_text"],
                    "rag_sources_used": rag_sources_used,
                    "rag_context_count": rag_context_count,
                },
                to=sid,
            )

            logger.info(
                "Response sent with RAG info",
                extra={
                    "sid": sid,
                    "rag_sources_used": rag_sources_used,
                    "rag_context_count": rag_context_count,
                },
            )

        # Send visual actions
        if result_state.get("visual_actions"):
            for action in result_state["visual_actions"]:
                await sio.emit(
                    "visual", {"action": action["action"], "payload": action["payload"]}, to=sid
                )

                logger.debug("Visual action sent", extra={"sid": sid, "action": action["action"]})

        # Send audio if available
        if result_state.get("audio_data"):
            audio_data = result_state["audio_data"]
            if audio_data is not None:
                audio_b64 = base64.b64encode(audio_data).decode()

            await sio.emit(
                "audio_response",
                {
                    "session_id": result_state["session_id"],
                    "data": audio_b64,
                    "format": "audio/mpeg",
                },
                to=sid,
            )

            logger.info(
                "Audio response sent",
                extra={"sid": sid, "audio_size": len(result_state.get("audio_data") or b"")},
            )

        # Send processing complete
        await sio.emit(
            "session_status",
            {
                "status": "complete",
                "processing_time_ms": int(result_state["processing_time"] * 1000),
                "turn_count": result_state["turn_count"],
            },
            to=sid,
        )

        logger.info(
            "Response sent successfully",
            extra={"sid": sid, "turn_count": result_state["turn_count"]},
        )

    except Exception as e:
        logger.error(
            "Process and respond failed",
            extra={"sid": sid, "error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )

        await sio.emit("error", {"message": f"Processing failed: {str(e)}"}, to=sid)


logger.debug("Socket.IO server created")
