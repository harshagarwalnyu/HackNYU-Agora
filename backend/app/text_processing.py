"""
Text processing utilities.
"""

import logging
from typing import List, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


def _find_sentence_boundary(chunk: str, start_pos: int, chunk_size: int, text_len: int) -> Tuple[str, int]:
    """
    Find a sentence boundary in the chunk to break at natural boundaries.
    
    Looks for period or newline as break points. Only breaks if found after
    the halfway point of chunk_size for safety.
    
    Args:
        chunk: Current chunk of text
        start_pos: Starting position in original text
        chunk_size: Configured chunk size threshold
        text_len: Total length of original text
    
    Returns:
        Tuple of (adjusted_chunk, new_end_position)
    """
    last_period = chunk.rfind(".")
    last_newline = chunk.rfind("\n")
    break_point = max(last_period, last_newline)

    # Only break if we found a boundary after the halfway point
    if break_point > chunk_size // 2:
        adjusted_chunk = chunk[:break_point + 1]
        new_end = start_pos + break_point + 1
        return adjusted_chunk, new_end
    
    return chunk, start_pos + len(chunk)


def chunk_text(
    text: str | None, chunk_size: int | None = None, overlap: int | None = None
) -> List[str]:
    """
    Chunk text into overlapping segments.

    Args:
        text: Input text
        chunk_size: Maximum chunk size in characters (defaults to config.chunk_size)
        overlap: Overlap between chunks (defaults to config.chunk_overlap)

    Returns:
        List of text chunks
    """
    # Use config defaults if not provided
    if chunk_size is None:
        chunk_size = settings.chunk_size
    if overlap is None:
        overlap = settings.chunk_overlap

    if not text or text.strip() == "":
        logger.warning("Empty text, returning empty list")
        return []

    logger.debug(
        "Chunking text",
        extra={"text_length": len(text), "chunk_size": chunk_size, "overlap": overlap},
    )

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]

        # Guard clause: try to break at sentence boundary if not at end of text
        if end < text_length:
            chunk, end = _find_sentence_boundary(chunk, start, chunk_size, text_length)

        chunk_stripped = chunk.strip()
        if chunk_stripped:
            chunks.append(chunk_stripped)

        # If we've reached the end of text, break to avoid creating overlapping chunks
        if end >= text_length:
            break
        
        # Ensure forward progress: advance by at least chunk_size - overlap
        start = max(start + 1, end - overlap)

    logger.info(
        "Text chunked",
        extra={
            "chunks_count": len(chunks),
            "avg_chunk_size": sum(len(c) for c in chunks) // len(chunks) if chunks else 0,
        },
    )

    return chunks
