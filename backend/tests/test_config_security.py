import os
import importlib
from unittest import mock

def test_debug_mode_is_false_by_default():
    """
    Test that debug mode is disabled by default for security.
    """
    # Set required env vars to satisfy validation and clear DEBUG to test default
    with mock.patch.dict(os.environ, {"GROQ_API_KEY": "mock_key"}):
        # Ensure DEBUG is not in env if it might be set
        os.environ.pop("DEBUG", None)
        import app.config
        # Reload to ensure settings are re-initialized with current env
        importlib.reload(app.config)
        from app.config import settings

        assert settings.debug is False, "Debug mode should be False by default"
