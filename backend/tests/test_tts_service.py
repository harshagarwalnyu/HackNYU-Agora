import unittest
from unittest.mock import patch
from app.services.tts_service import EdgeTTS

# Mock dependencies used globally or during initialization if needed
# But better to patch them where they are used.

class TestEdgeTTS(unittest.IsolatedAsyncioTestCase):
    @patch("app.services.tts_service.edge_tts.Communicate")
    async def test_edge_tts_synthesize_success(self, mock_communicate_class):
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

        # Setup the mock Communicate instance
        mock_instance = mock_communicate_class.return_value
        mock_instance.stream = mock_stream

        # Act
        result = await tts.synthesize("Hello world")

        # Assert
        self.assertEqual(result, b"chunk1chunk2")
        mock_communicate_class.assert_called_once_with("Hello world", tts.voice)

    @patch("app.services.tts_service.edge_tts.Communicate")
    async def test_edge_tts_synthesize_empty_audio(self, mock_communicate_class):
        # Arrange
        tts = EdgeTTS()

        async def mock_stream_empty():
            if False:
                yield {}

        # Setup the mock Communicate instance
        mock_instance = mock_communicate_class.return_value
        mock_instance.stream = mock_stream_empty

        # Act & Assert
        with self.assertRaisesRegex(RuntimeError, "Edge TTS produced empty audio"):
            await tts.synthesize("Hello world")

if __name__ == "__main__":
    unittest.main()
