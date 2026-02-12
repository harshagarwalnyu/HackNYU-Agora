"""
Materials API - File upload and processing endpoints.
Handles PDFs, PPTs, images, and text documents with Docling parsing.
"""

import logging
import uuid
from pathlib import Path

from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.config import settings
from app.workers.chunk_ingest import process_document

logger = logging.getLogger(__name__)

router = APIRouter()


# In-memory upload status tracking (use Redis/DB in production)
upload_status = {}


@router.post("/upload")
async def upload_materials(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    course_id: str = Form(default="general"),
    description: str = Form(default=""),
):
    """
    Upload study materials for processing.

    Args:
        file: Uploaded file (PDF, PPT, image, etc.)
        user_id: User identifier
        course_id: Course/topic identifier
        description: Optional description

    Returns:
        Upload status with job_id
    """
    try:
        logger.info("=" * 80)
        logger.info("MATERIALS UPLOAD REQUEST")
        logger.info("=" * 80)
        logger.debug(
            "Upload materials request",
            extra={
                "file_name": file.filename,
                "content_type": file.content_type,
                "user_id": user_id,
                "course_id": course_id,
                "description": description,
            },
        )

        # Validate file
        if not file.filename:
            logger.error("No filename provided")
            raise HTTPException(status_code=400, detail="No filename provided")

        # Check file size
        content = await file.read()
        file_size = len(content)

        logger.debug(
            "File read",
            extra={"size_bytes": file_size, "size_mb": round(file_size / (1024 * 1024), 2)},
        )

        if file_size > settings.upload_max_size:
            logger.error(
                "File too large",
                extra={"file_size": file_size, "max_size": settings.upload_max_size},
            )
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.upload_max_size / (1024 * 1024)}MB",
            )

        # Generate job ID
        job_id = str(uuid.uuid4())

        logger.debug("Job ID generated", extra={"job_id": job_id})

        # Save file to storage
        file_ext = Path(file.filename).suffix
        storage_path = settings.storage_path / user_id / course_id
        storage_path.mkdir(parents=True, exist_ok=True)

        file_path = storage_path / f"{job_id}{file_ext}"

        logger.debug("Saving file to storage", extra={"file_path_str": str(file_path)})

        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(
            "File saved successfully",
            extra={"file_path_str": str(file_path), "size_bytes": file_size},
        )

        # Update status
        upload_status[job_id] = {
            "job_id": job_id,
            "status": "processing",
            "filename": file.filename,
            "user_id": user_id,
            "course_id": course_id,
            "progress": 0,
            "message": "Processing document...",
        }

        logger.debug(
            "Status tracking initialized", extra={"job_id": job_id, "status": "processing"}
        )

        # Process document asynchronously (in background)
        import asyncio

        async def process_in_background():
            try:
                logger.debug("Starting background processing", extra={"job_id": job_id})

                await process_document(
                    file_path=str(file_path),
                    user_id=user_id,
                    course_id=course_id,
                    job_id=job_id,
                    status_callback=lambda progress, msg: upload_status.update(
                        {job_id: {**upload_status[job_id], "progress": progress, "message": msg}}
                    ),
                )

                upload_status[job_id]["status"] = "completed"
                upload_status[job_id]["progress"] = 100
                upload_status[job_id]["message"] = "Processing complete"

                logger.info("Background processing completed", extra={"job_id": job_id})

            except Exception as e:
                logger.error(
                    "Background processing failed",
                    extra={"job_id": job_id, "error": str(e), "error_type": type(e).__name__},
                    exc_info=True,
                )

                upload_status[job_id]["status"] = "failed"
                upload_status[job_id]["message"] = f"Error: {str(e)}"

        # Fire and forget
        asyncio.create_task(process_in_background())

        logger.info(
            "Upload accepted, processing started",
            extra={"job_id": job_id, "file_name": file.filename},
        )
        logger.info("=" * 80)

        return JSONResponse(
            content={
                "job_id": job_id,
                "status": "processing",
                "message": "File uploaded successfully. Processing started.",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Upload failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "file_name": file.filename if file else "unknown",
            },
            exc_info=True,
        )

        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/status/{job_id}")
async def get_upload_status(job_id: str):
    """
    Get the status of an upload job.

    Args:
        job_id: Job identifier

    Returns:
        Job status information
    """
    try:
        logger.debug("Status check request", extra={"job_id": job_id})

        if job_id not in upload_status:
            logger.warning("Job ID not found", extra={"job_id": job_id})
            raise HTTPException(status_code=404, detail="Job not found")

        status = upload_status[job_id]

        logger.debug(
            "Status retrieved",
            extra={
                "job_id": job_id,
                "status": status["status"],
                "progress": status.get("progress", 0),
            },
        )

        return JSONResponse(content=status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Status check failed",
            extra={"error": str(e), "error_type": type(e).__name__, "job_id": job_id},
            exc_info=True,
        )

        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.get("/list")
async def list_materials(user_id: str, course_id: Optional[str] = None):
    """
    List uploaded materials for a user.

    Args:
        user_id: User identifier
        course_id: Optional course filter

    Returns:
        List of materials
    """
    try:
        logger.debug("List materials request", extra={"user_id": user_id, "course_id": course_id})

        # Filter uploads for this user
        user_uploads = [
            status
            for status in upload_status.values()
            if status["user_id"] == user_id
            and (course_id is None or status["course_id"] == course_id)
        ]

        logger.info(
            "Materials listed",
            extra={"user_id": user_id, "course_id": course_id, "count": len(user_uploads)},
        )

        return JSONResponse(content={"materials": user_uploads, "count": len(user_uploads)})

    except Exception as e:
        logger.error(
            "List materials failed",
            extra={"error": str(e), "error_type": type(e).__name__, "user_id": user_id},
            exc_info=True,
        )

        raise HTTPException(status_code=500, detail=f"List failed: {str(e)}")


logger.debug("Materials API router created")
