"""
Text processing utilities.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


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
    logger.debug(
        "Chunking text",
        extra={"text_length": len(text), "chunk_size": chunk_size, "overlap": overlap},
    )

    if not text or text.strip() == "":
        logger.warning("Empty text, returning empty list")
        return []

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

        chunk_stripped = chunk.strip()
        if chunk_stripped:
            chunks.append(chunk_stripped)

        # Ensure we always make forward progress
        new_start = end - overlap
        if new_start <= start:
             # If overlap is too large relative to chunk size or we broke early,
             # we might not advance. Force advance by at least 1.
             new_start = start + 1

        start = new_start

    logger.info(
        "Text chunked",
        extra={
            "chunks_count": len(chunks),
            "avg_chunk_size": sum(len(c) for c in chunks) // len(chunks) if chunks else 0,
        },
    )

    return chunks
