import os
import importlib
from unittest import mock

def test_debug_mode_is_false_by_default():
    """
    Test that debug mode is disabled by default for security.
    """
    # Set required env vars to satisfy validation
    with mock.patch.dict(os.environ, {"GROQ_API_KEY": "dummy"}):
        import backend.app.config
        # Reload to ensure settings are re-initialized with current env
        importlib.reload(backend.app.config)
        from backend.app.config import settings

        assert settings.debug is False, "Debug mode should be False by default"
