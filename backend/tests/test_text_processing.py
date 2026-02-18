
import sys
import os

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.text_processing import chunk_text

def test_chunk_text_normal():
    text = "This is a long text that needs to be chunked into smaller pieces."
    chunks = chunk_text(text, chunk_size=20, overlap=5)

    assert len(chunks) > 0
    for chunk in chunks:
        assert len(chunk) <= 20
        assert len(chunk) > 0

def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []

def test_chunk_text_short():
    text = "Short text"
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    assert len(chunks) == 1
    assert chunks[0] == "Short text"

def test_chunk_text_sentence_boundary():
    text = "First sentence. Second sentence."
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    assert chunks[0] == "First sentence."

    # Second sentence might be split because chunk_size=20 is small
    combined = " ".join(chunks)
    assert "Second" in combined
    assert "sentence." in combined

def test_chunk_text_overlap_bug():
    """
    Test the scenario where overlap is large relative to the effective chunk size
    """
    chunk_size = 10
    overlap = 8
    text = "aaaaaa. bbbbb"

    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    # Check for regressions
    assert "" not in chunks, "Should not produce empty chunks"
    assert len(chunks) > 0

    combined = "".join(chunks)
    assert "aaaaaa." in combined
    assert "bbbbb" in combined

def test_chunk_text_infinite_loop_potential():
    """
    Another edge case where overlap equals chunk size
    """
    text = "abcde"
    chunks = chunk_text(text, chunk_size=5, overlap=5)

    assert len(chunks) > 0
    assert chunks[0] == "abcde"
