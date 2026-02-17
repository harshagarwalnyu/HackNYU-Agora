"""
Document ingestion worker using Docling 2.0.
Parses PDFs, images, and other documents, chunks them, generates embeddings, and stores in Qdrant.
"""

import logging
import asyncio
import uuid
from pathlib import Path
from typing import Callable, List, Optional

import aiofiles
from app.services.llm_client import llm_client
from app.services.qdrant_client import qdrant_service
from app.utils.text_processing import chunk_text

logger = logging.getLogger(__name__)


async def process_document(
    file_path: str,
    user_id: str,
    course_id: str,
    job_id: str,
    status_callback: Optional[Callable[[int, str], None]] = None,
) -> None:
    """
    Process a document: parse, chunk, embed, and store.

    Args:
        file_path: Path to the document file
        user_id: User identifier
        course_id: Course identifier
        job_id: Job identifier for tracking
        status_callback: Optional callback for progress updates
    """
    try:
        logger.info("=" * 80)
        logger.info("DOCUMENT PROCESSING START")
        logger.info("=" * 80)
        logger.debug(
            "Starting document processing",
            extra={
                "file_path": file_path,
                "user_id": user_id,
                "course_id": course_id,
                "job_id": job_id,
            },
        )

        def update_status(progress: int, message: str) -> None:
            """Update status via callback."""
            logger.debug(
                "Progress update",
                extra={"job_id": job_id, "progress": progress, "status_message": message},
            )
            if status_callback:
                status_callback(progress, message)

        update_status(10, "Parsing document...")

        # Parse document with Docling
        logger.debug("Parsing document with Docling...")
        parsed_content = await parse_with_docling(file_path)

        logger.info(
            "Document parsed",
            extra={"content_length": len(parsed_content), "content_preview": parsed_content[:200]},
        )

        update_status(40, "Chunking content...")

        # Chunk the content
        logger.debug("Chunking content...")
        chunks = chunk_text(parsed_content, chunk_size=512, overlap=50)

        logger.info("Content chunked", extra={"chunks_count": len(chunks)})

        update_status(60, f"Generating embeddings for {len(chunks)} chunks...")

        # Generate embeddings and prepare for Qdrant
        logger.debug("Generating embeddings for all chunks...")

        async def process_chunk(idx, chunk_content):
            logger.debug(
                f"Embedding chunk {idx + 1}/{len(chunks)}",
                extra={"chunk_index": idx, "chunk_length": len(chunk_content)},
            )

            # Generate embedding
            embedding = await llm_client.embed_text(chunk_content)

            # Create chunk data - use UUID for Qdrant point ID
            chunk_id = str(uuid.uuid4())

            logger.debug(
                f"Chunk {idx + 1} embedded",
                extra={"chunk_id": chunk_id, "embedding_dim": len(embedding)},
            )

            return {
                "id": chunk_id,
                "text": chunk_content,
                "embedding": embedding,
                "metadata": {
                    "source_file": Path(file_path).name,
                    "chunk_index": idx,
                    "job_id": job_id,
                },
            }

        # Process all chunks in parallel
        chunk_data = await asyncio.gather(*(process_chunk(idx, content) for idx, content in enumerate(chunks)))

        logger.info("All embeddings generated", extra={"chunks_count": len(chunk_data)})

        update_status(80, "Storing in vector database...")

        # Store in Qdrant
        logger.debug("Upserting chunks to Qdrant...")
        await qdrant_service.upsert_notes(user_id=user_id, course_id=course_id, chunks=chunk_data)

        logger.info(
            "Chunks stored in Qdrant",
            extra={"user_id": user_id, "course_id": course_id, "chunks_count": len(chunk_data)},
        )

        update_status(100, "Processing complete!")

        logger.info("=" * 80)
        logger.info("DOCUMENT PROCESSING COMPLETE")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(
            "Document processing failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "file_path": file_path,
                "user_id": user_id,
                "job_id": job_id,
            },
            exc_info=True,
        )

        if status_callback:
            status_callback(0, f"Error: {str(e)}")

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
        logger.error(
            "Docling parsing failed",
            extra={"error": str(e), "error_type": type(e).__name__, "file_path": file_path},
            exc_info=True,
        )

        # Try fallback
        logger.warning("Attempting fallback parser...")
        return await parse_fallback(file_path)


async def parse_fallback(file_path: str) -> str:
    """
    Fallback parser for when Docling fails.
    Handles images via Gemini vision and text files directly.

    Args:
        file_path: Path to file

    Returns:
        Extracted text
    """
    try:
        logger.debug("Using fallback parser", extra={"file_path": file_path})

        path = Path(file_path)
        suffix = path.suffix.lower()

        # Image files - use Gemini vision
        if suffix in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
            logger.debug("Parsing image with Gemini vision...")

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

            logger.info("Image parsed with Gemini", extra={"content_length": len(content)})

            return content

        # Text files
        elif suffix in [".txt", ".md", ".markdown"]:
            logger.debug("Reading text file...")

            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()

            logger.info("Text file read", extra={"content_length": len(content)})

            return content

        # PDFs - basic extraction
        elif suffix == ".pdf":
            logger.debug("Parsing PDF with PyPDF2...")

            try:
                import PyPDF2

                with open(file_path, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text_parts = []

                    for page_num, page in enumerate(pdf_reader.pages):
                        text = page.extract_text()
                        text_parts.append(text)

                        logger.debug(
                            f"Extracted page {page_num + 1}", extra={"text_length": len(text)}
                        )

                    content = "\n\n".join(text_parts)

                    logger.info(
                        "PDF parsed",
                        extra={
                            "pages_count": len(pdf_reader.pages),
                            "content_length": len(content),
                        },
                    )

                    return content

            except ImportError:
                logger.error("PyPDF2 not available")
                raise RuntimeError("PDF parsing not available. Install PyPDF2 or Docling.")

        else:
            logger.error(f"Unsupported file type: {suffix}")
            raise ValueError(f"Unsupported file type: {suffix}")

    except Exception as e:
        logger.error(
            "Fallback parsing failed",
            extra={"error": str(e), "error_type": type(e).__name__, "file_path": file_path},
            exc_info=True,
        )
        raise


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """
    Chunk text into overlapping segments.

    Args:
        text: Input text
        chunk_size: Maximum chunk size in characters
        overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    if not text or text.strip() == "":
        logger.warning("Empty text, returning empty list")
        return []

    logger.debug(
        "Chunking text",
        extra={"text_length": len(text), "chunk_size": chunk_size, "overlap": overlap},
    )

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind(".")
            last_newline = chunk.rfind("\n")
            break_point = max(last_period, last_newline)

            if break_point > chunk_size // 2:  # Only break if reasonable
                chunk = text[start : start + break_point + 1]
                end = start + break_point + 1

        chunks.append(chunk.strip())

        start = end - overlap

    logger.info(
        "Text chunked",
        extra={
            "chunks_count": len(chunks),
            "avg_chunk_size": sum(len(c) for c in chunks) // len(chunks) if chunks else 0,
        },
    )

    return chunks


logger.debug("Chunk ingest worker module loaded")
