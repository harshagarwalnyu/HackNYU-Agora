import sys
import unittest
from unittest.mock import MagicMock, AsyncMock

# Mock dependencies before they are imported
mock_edge_tts = MagicMock()
sys.modules["edge_tts"] = mock_edge_tts

mock_pydantic = MagicMock()
sys.modules["pydantic"] = mock_pydantic
sys.modules["pydantic_settings"] = MagicMock()

mock_config = MagicMock()
mock_config.settings.tts_voice = "en-US-AriaNeural"
sys.modules["app.config"] = mock_config

from app.services.tts_service import EdgeTTS

class TestEdgeTTS(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        mock_edge_tts.Communicate.reset_mock()

    async def test_edge_tts_synthesize_success(self):
        # Arrange
        tts = EdgeTTS()
        mock_chunks = [
            {"type": "audio", "data": b"chunk1"},
            {"type": "other", "data": b"metadata"},
            {"type": "audio", "data": b"chunk2"},
        ]

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        # Setup the mock Communicate in the already mocked edge_tts
        mock_communicate_class = mock_edge_tts.Communicate
        mock_instance = mock_communicate_class.return_value
        mock_instance.stream = mock_stream

        # Act
        result = await tts.synthesize("Hello world")

        # Assert
        self.assertEqual(result, b"chunk1chunk2")
        mock_communicate_class.assert_called_once_with("Hello world", tts.voice)

    async def test_edge_tts_synthesize_empty_audio(self):
        # Arrange
        tts = EdgeTTS()

        async def mock_stream_empty():
            if False:
                yield {}

        # Setup the mock Communicate in the already mocked edge_tts
        mock_communicate_class = mock_edge_tts.Communicate
        mock_instance = mock_communicate_class.return_value
        mock_instance.stream = mock_stream_empty

        # Act & Assert
        with self.assertRaisesRegex(RuntimeError, "Edge TTS produced empty audio"):
            await tts.synthesize("Hello world")

if __name__ == "__main__":
    unittest.main()
