import sys
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Fixture to setup isolated environment and import module
@pytest.fixture
def chunk_ingest_module():
    """
    Returns the app.chunk_ingest module.
    Mocks for services should be applied using patch() in individual tests.
    """
    import app.chunk_ingest
    return app.chunk_ingest

@pytest.mark.asyncio
@patch("app.chunk_ingest.llm_client")
async def test_parse_fallback_image(mock_llm_client, chunk_ingest_module):
    """Test fallback parsing for image files using Gemini."""
    parse_fallback = chunk_ingest_module.parse_fallback
    llm_client = mock_llm_client

    file_path = "test_image.jpg"
    image_content = b"fake_image_content"
    expected_text = "Extracted text from image"

    # Setup mock behavior
    llm_client.analyze_image = AsyncMock(return_value=expected_text)

    # Mock aiofiles.open
    mock_file = AsyncMock()
    mock_file.read.return_value = image_content

    mock_ctx = MagicMock()
    mock_ctx.__aenter__.return_value = mock_file
    mock_ctx.__aexit__.return_value = None

    with patch("aiofiles.open", return_value=mock_ctx) as mock_open:
        result = await parse_fallback(file_path)

        assert result == expected_text
        mock_open.assert_called_with(file_path, "rb")
        mock_file.read.assert_called_once()
        llm_client.analyze_image.assert_called_once()

        # Verify args to analyze_image
        call_args = llm_client.analyze_image.call_args
        assert call_args.kwargs["image_data"] == image_content
        assert call_args.kwargs["mime_type"] == "image/jpg"

@pytest.mark.asyncio
async def test_parse_fallback_text(chunk_ingest_module):
    """Test fallback parsing for text files."""
    parse_fallback = chunk_ingest_module.parse_fallback

    file_path = "test_doc.txt"
    file_content = "This is a text file content."

    mock_file = AsyncMock()
    mock_file.read.return_value = file_content

    mock_ctx = MagicMock()
    mock_ctx.__aenter__.return_value = mock_file
    mock_ctx.__aexit__.return_value = None

    with patch("aiofiles.open", return_value=mock_ctx) as mock_open:
        result = await parse_fallback(file_path)

        assert result == file_content
        mock_open.assert_called_with(file_path, "r", encoding="utf-8")

@pytest.mark.asyncio
async def test_parse_fallback_pdf_success(chunk_ingest_module):
    """Test fallback parsing for PDF files using PyPDF2."""
    parse_fallback = chunk_ingest_module.parse_fallback

    file_path = "test_doc.pdf"
    expected_text = "Page 1 content\n\nPage 2 content"

    # Mock PyPDF2
    mock_pypdf2 = MagicMock()
    mock_reader = MagicMock()

    page1 = MagicMock()
    page1.extract_text.return_value = "Page 1 content"
    page2 = MagicMock()
    page2.extract_text.return_value = "Page 2 content"

    mock_reader.pages = [page1, page2]
    mock_pypdf2.PdfReader.return_value = mock_reader

    # We must patch sys.modules so 'import PyPDF2' inside the function works
    with patch.dict(sys.modules, {"PyPDF2": mock_pypdf2}):
        # Mock built-in open used by PyPDF2 logic
        mock_file_obj = MagicMock()
        mock_file_obj.__enter__.return_value = mock_file_obj
        mock_file_obj.__exit__.return_value = None

        with patch("builtins.open", return_value=mock_file_obj) as mock_open:
            result = await parse_fallback(file_path)

            assert result == expected_text
            mock_open.assert_called_with(file_path, "rb")
            mock_pypdf2.PdfReader.assert_called_with(mock_file_obj)

@pytest.mark.asyncio
async def test_parse_fallback_pdf_missing_dependency(chunk_ingest_module):
    """Test fallback parsing for PDF when PyPDF2 is missing."""
    parse_fallback = chunk_ingest_module.parse_fallback

    file_path = "test_doc.pdf"

    # Ensure PyPDF2 import fails
    with patch.dict(sys.modules):
        if "PyPDF2" in sys.modules:
            del sys.modules["PyPDF2"]

        # Mock built-in __import__ to raise ImportError for PyPDF2
        original_import = __import__
        def side_effect(name, *args, **kwargs):
            if name == "PyPDF2":
                raise ImportError("No module named 'PyPDF2'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=side_effect):
             with pytest.raises(RuntimeError, match="PDF parsing not available"):
                await parse_fallback(file_path)

@pytest.mark.asyncio
async def test_parse_fallback_unsupported(chunk_ingest_module):
    """Test fallback parsing for unsupported file types."""
    parse_fallback = chunk_ingest_module.parse_fallback

    with pytest.raises(ValueError, match="Unsupported file type"):
        await parse_fallback("test.exe")
