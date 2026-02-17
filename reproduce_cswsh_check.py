
import sys
import os
from unittest.mock import MagicMock

# Set python path to include backend
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mock settings with WILDCARD
settings_mock = MagicMock()
settings_mock.backend_cors_origins = ["*"]
settings_mock.log_level = "DEBUG"

# Mock app.config
config_module = MagicMock()
config_module.settings = settings_mock
sys.modules['app.config'] = config_module

# Mock other dependencies
sys.modules['app.graph.state'] = MagicMock()
sys.modules['app.graph.builder'] = MagicMock()
sys.modules['app.services.stt_service'] = MagicMock()
sys.modules['fastapi'] = MagicMock()

try:
    if 'app.api.ws' in sys.modules:
        del sys.modules['app.api.ws']

    from app.api import ws
    # Check eio.cors_allowed_origins
    cors = ws.sio.eio.cors_allowed_origins
    print(f"Current cors_allowed_origins: {cors}")

    if cors == ["*"]:
        print("VULNERABLE: Wildcard allowed")
    elif cors is None:
        print("SECURE: None enforces same-origin check.")
    else:
        print(f"Other: {cors}")

except Exception as e:
    print(f"Error during import: {e}")
