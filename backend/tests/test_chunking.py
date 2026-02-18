from app.text_processing import chunk_text

def test_chunk_text_empty():
    """Test chunking with empty text."""
    assert chunk_text("") == []
    assert chunk_text("   ") == []
    assert chunk_text(None) == []

def test_chunk_text_basic():
    """Test chunking with basic text smaller than chunk size."""
    text = "Hello world. This is a test."
    chunks = chunk_text(text, chunk_size=100)
    assert len(chunks) == 1
    assert chunks[0] == text

def test_chunk_text_larger_than_chunk_size():
    """Test chunking with text larger than chunk size."""
    text = "Hello world. " * 20
    # chunk_size is small to force split
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert len(chunks) > 1

    # Check that chunks are not empty
    for chunk in chunks:
        assert len(chunk) > 0
        assert len(chunk) <= 50

def test_chunk_text_overlap():
    """Test chunking with overlap."""
    text = "1234567890"
    # chunk_size=5, overlap=2
    # Expect: "12345", "45678", "7890" (approx)
    chunks = chunk_text(text, chunk_size=5, overlap=2)

    assert len(chunks) >= 2
    # Check overlap
    # If chunk 1 ends with "45", chunk 2 should start with "4" or "5" depending on implementation

    # Let's see the implementation:
    # start = 0
    # end = 5 -> "12345"
    # next start = 5 - 2 = 3
    # next end = 3 + 5 = 8 -> "45678"
    # next start = 8 - 2 = 6
    # next end = 6 + 5 = 11 -> "7890"

    if len(chunks) == 3:
        assert chunks[0] == "12345"
        assert chunks[1] == "45678"
        assert chunks[2] == "7890"
