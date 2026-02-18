"""
Document ingestion worker using Docling 2.0.
Parses PDFs, images, and other documents, chunks them, generates embeddings, and stores in Qdrant.
"""

import logging
import asyncio
import uuid
from pathlib import Path
from typing import Any, Callable, Optional, Coroutine

import aiofiles
from app.config import IMAGE_EXTENSIONS, TEXT_EXTENSIONS, DOCUMENT_EXTENSIONS, settings
from app.services.llm_client import llm_client
from app.services.qdrant_client import qdrant_service
from app.text_processing import chunk_text
from app.logging_config import log_exception

logger = logging.getLogger(__name__)


def _update_status(
    progress: int,
    message: str,
    job_id: str,
    status_callback: Optional[Callable[[int, str], None]] = None,
) -> None:
    """
    Update job status with progress information.

    Args:
        progress: Progress percentage (0-100)
        message: Status message
        job_id: Job identifier for logging context
        status_callback: Optional callback to notify client
    """
    logger.debug(
        "Status update",
        extra={"job_id": job_id, "progress": progress, "message": message},
    )
    if status_callback:
        status_callback(progress, message)


def _build_chunk_metadata(
    chunk_index: int,
    file_path: str,
    job_id: str,
) -> dict[str, Any]:
    """
    Build metadata dictionary for a chunk.

    Args:
        chunk_index: Index of the chunk
        file_path: Source file path
        job_id: Job identifier

    Returns:
        Metadata dictionary
    """
    return {
        "source_file": Path(file_path).name,
        "chunk_index": chunk_index,
        "job_id": job_id,
    }


async def _embed_single_chunk(
    chunk_index: int,
    chunk_content: str,
    file_path: str,
    job_id: str,
    total_chunks: int,
) -> dict[str, Any]:
    """
    Generate embedding for a single chunk.

    Args:
        chunk_index: Index of the chunk (0-based)
        chunk_content: Text content of the chunk
        file_path: Source file path
        job_id: Job identifier
        total_chunks: Total number of chunks for logging

    Returns:
        Dictionary with chunk ID, text, embedding, and metadata
    """
    logger.debug(
        f"Embedding chunk {chunk_index + 1}/{total_chunks}",
        extra={"chunk_index": chunk_index, "chunk_length": len(chunk_content)},
    )

    # Generate embedding
    embedding = await llm_client.embed_text(chunk_content)

    # Create chunk data - use UUID for Qdrant point ID
    chunk_id = str(uuid.uuid4())

    logger.debug(
        f"Chunk {chunk_index + 1} embedded",
        extra={"chunk_id": chunk_id, "embedding_dim": len(embedding)},
    )

    return {
        "id": chunk_id,
        "text": chunk_content,
        "embedding": embedding,
        "metadata": _build_chunk_metadata(chunk_index, file_path, job_id),
    }


async def _generate_embeddings(
    chunks: list[str],
    file_path: str,
    job_id: str,
) -> list[dict[str, Any]]:
    """
    Generate embeddings for all chunks in a single batch.

    Args:
        chunks: List of text chunks
        file_path: Source file path
        job_id: Job identifier

    Returns:
        List of chunk data with embeddings
    """
    logger.debug(f"Generating batch embeddings for {len(chunks)} chunks...")

    # Generate all embeddings in one call
    embeddings = await llm_client.embed_batch(chunks)

    # Build chunk data objects
    chunk_data = []
    for idx, (content, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_id = str(uuid.uuid4())
        chunk_data.append({
            "id": chunk_id,
            "text": content,
            "embedding": embedding,
            "metadata": _build_chunk_metadata(idx, file_path, job_id),
        })

    logger.info("All embeddings generated", extra={"chunks_count": len(chunk_data)})

    return chunk_data


async def process_document(
    file_path: str,
    user_id: str,
    course_id: str,
    job_id: str,
    status_callback: Optional[Callable[[int, str], None]] = None,
) -> None:
    """
    Process a document: parse, chunk, embed, and store.

    Pipeline:
    1. Parse document (Docling with fallback)
    2. Chunk content
    3. Generate embeddings in parallel
    4. Store in Qdrant vector database

    Args:
        file_path: Path to the document file
        user_id: User identifier
        course_id: Course identifier
        job_id: Job identifier for tracking
        status_callback: Optional callback for progress updates

    Raises:
        Exception: Any parsing, embedding, or storage error
    """
    try:
        logger.info("=" * 80)
        logger.info("DOCUMENT PROCESSING START")
        logger.info("=" * 80)
        logger.debug(
            "Processing document",
            extra={
                "file_path": file_path,
                "user_id": user_id,
                "course_id": course_id,
                "job_id": job_id,
            },
        )

        # Step 1: Parse
        _update_status(10, "Parsing document...", job_id, status_callback)
        logger.debug("Parsing document with Docling...")
        parsed_content = await parse_with_docling(file_path)
        logger.info(
            "Document parsed",
            extra={"content_length": len(parsed_content)},
        )

        # Step 2: Chunk
        _update_status(40, "Chunking content...", job_id, status_callback)
        logger.debug("Chunking content...")
        chunks = chunk_text(parsed_content, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap)
        logger.info("Content chunked", extra={"chunks_count": len(chunks)})

        # Step 3: Embed
        _update_status(
            60,
            f"Generating embeddings for {len(chunks)} chunks...",
            job_id,
            status_callback,
        )
        chunk_data = await _generate_embeddings(chunks, file_path, job_id)

        # Step 4: Store
        _update_status(80, "Storing in vector database...", job_id, status_callback)
        logger.debug("Upserting chunks to Qdrant...")
        await qdrant_service.upsert_notes(
            user_id=user_id,
            course_id=course_id,
            chunks=chunk_data,
        )
        logger.info(
            "Chunks stored in Qdrant",
            extra={
                "user_id": user_id,
                "course_id": course_id,
                "chunks_count": len(chunk_data),
            },
        )

        _update_status(100, "Processing complete!", job_id, status_callback)

        logger.info("=" * 80)
        logger.info("DOCUMENT PROCESSING COMPLETE")
        logger.info("=" * 80)

    except Exception as e:
        log_exception(
            logger,
            "Document processing failed",
            e,
            {
                "file_path": file_path,
                "user_id": user_id,
                "job_id": job_id,
            },
        )
        _update_status(0, f"Error: {str(e)}", job_id, status_callback)
        raise


async def parse_with_docling(file_path: str) -> str:
    """
    Parse document using Docling 2.0.

    Args:
        file_path: Path to document

    Returns:
        Extracted text content
    """
    try:
        logger.debug("Parsing with Docling", extra={"file_path": file_path})

        from docling.document_converter import DocumentConverter

        # Initialize converter
        converter = DocumentConverter()

        logger.debug("Docling converter initialized")

        # Convert document
        logger.debug("Converting document...")
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, converter.convert, file_path)

        logger.debug("Document converted", extra={"has_result": result is not None})

        # Extract markdown text
        markdown_text = result.document.export_to_markdown()

        logger.info(
            "Docling parsing completed",
            extra={"file_path": file_path, "content_length": len(markdown_text)},
        )

        return markdown_text

    except ImportError as e:
        logger.error(
            "Docling import failed - falling back to basic parsing", extra={"error": str(e)}
        )
        # Fallback to basic parsing
        return await parse_fallback(file_path)

    except Exception as e:
        log_exception(logger, "Docling parsing failed", e, {"file_path": file_path})
        # Try fallback
        logger.warning("Attempting fallback parser...")
        return await parse_fallback(file_path)


async def _parse_image(file_path: str, suffix: str) -> str:
    """Parse image file using LLM vision."""
    logger.debug("Parsing image with LLM vision...")

    async with aiofiles.open(file_path, "rb") as f:
        image_data = await f.read()

    prompt = """Extract all text and content from this image.
If it contains:
- Handwritten notes: transcribe them
- Diagrams: describe them in detail
- Formulas: write them in LaTeX or text format
- Tables: format them as markdown tables

Provide a comprehensive markdown representation of everything in the image."""

    content = await llm_client.analyze_image(
        image_data=image_data, prompt=prompt, mime_type=f"image/{suffix[1:]}"
    )

    logger.info("Image parsed with LLM vision", extra={"content_length": len(content)})
    return content


async def _parse_text(file_path: str) -> str:
    """Parse plain text file."""
    logger.debug("Reading text file...")

    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
        content: str = await f.read()

    logger.info("Text file read", extra={"content_length": len(content)})
    return content


async def _parse_pdf(file_path: str) -> str:
    """Parse PDF using PyPDF2."""
    logger.debug("Parsing PDF with PyPDF2...")

    try:
        import PyPDF2
    except ImportError:
        logger.error("PyPDF2 not available")
        raise RuntimeError("PDF parsing not available. Install PyPDF2 or Docling.")

    with open(file_path, "rb") as f:
        pdf_reader = PyPDF2.PdfReader(f)
        text_parts: list[str] = []
        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            logger.debug(
                f"Extracted page {page_num + 1}",
                extra={"text_length": len(text) if text else 0},
            )
            if text:
                text_parts.append(text)

        content = "\n\n".join(text_parts)

        logger.info(
            "PDF parsed",
            extra={
                "pages_count": len(pdf_reader.pages),
                "content_length": len(content),
            },
        )

        return content


async def parse_fallback(file_path: str) -> str:
    """
    Fallback parser for when Docling fails.
    Dispatches to appropriate parser based on file type.

    Args:
        file_path: Path to file

    Returns:
        Extracted text
    """
    try:
        logger.debug("Using fallback parser", extra={"file_path": file_path})

        path = Path(file_path)
        suffix = path.suffix.lower()

        # Dispatch table: suffix -> parser function
        # Use file extension constants from config

        parser_map: dict[str, Callable[..., Coroutine[Any, Any, str]]] = {}
        
        # Map image extensions to image parser
        for ext in IMAGE_EXTENSIONS:
            parser_map[ext] = _parse_image
        
        # Map text extensions to text parser
        for ext in TEXT_EXTENSIONS:
            parser_map[ext] = _parse_text
        
        # Map document extensions to document parser
        for ext in DOCUMENT_EXTENSIONS:
            parser_map[ext] = _parse_pdf

        parser = parser_map.get(suffix)
        if not parser:
            logger.error(f"Unsupported file type: {suffix}")
            raise ValueError(f"Unsupported file type: {suffix}")

        # Call appropriate parser with file_path and suffix if needed
        if parser == _parse_image:
            return await parser(file_path, suffix)
        else:
            return await parser(file_path)

    except Exception as e:
        log_exception(logger, "Fallback parsing failed", e, {"file_path": file_path})
        raise


logger.debug("Chunk ingest worker module loaded")
