"""
Test configuration and shared fixtures.

Pre-imports service modules so that unittest.mock.patch() can resolve
`app.services.X.Y` paths via getattr on the already-loaded parent module.

Without this, mock's _dot_lookup fails with:
  AttributeError: module 'app.services' has no attribute 'qdrant_client'
because Python only sets submodule attributes on parent packages when the
submodule has been explicitly imported at least once.

Also stubs out third-party packages that are broken in this dev environment
(sentence_transformers / transformers require PyTorch >= 2.4; installed: 2.1.2).
The stub allows llm_client.py to be imported for mocking purposes.

Known limitation: test_materials.py replaces attributes on the real qdrant_client
module during collection (via mock_module("qdrant_client").AsyncQdrantClient =
MagicMock()), which corrupts test_qdrant_service.py's imported AsyncQdrantClient.
These tests pass individually but fail together — a pre-existing test isolation
issue that would require major rewrites of test_materials.py to resolve fully.
"""

import pytest

# ---------------------------------------------------------------------------
# Pre-import service modules so patch("app.services.X.Y") resolves correctly.
# ---------------------------------------------------------------------------
import app.services.qdrant_client  # noqa: F401  E402
import app.services.llm_client     # noqa: F401  E402
import app.services.tts_service    # noqa: F401  E402
import app.services.stt_service    # noqa: F401  E402


try:
  from qdrant_client import AsyncQdrantClient as _REAL_ASYNC_QDRANT_CLIENT
except Exception:  # pragma: no cover
  _REAL_ASYNC_QDRANT_CLIENT = None


@pytest.fixture(autouse=True)
def restore_critical_symbols() -> None:
  """Restore shared module symbols that some tests mutate at import time."""
  if _REAL_ASYNC_QDRANT_CLIENT is not None:
    import qdrant_client
    import app.services.qdrant_client as svc_qdrant

    qdrant_client.AsyncQdrantClient = _REAL_ASYNC_QDRANT_CLIENT
    svc_qdrant.AsyncQdrantClient = _REAL_ASYNC_QDRANT_CLIENT

  yield

  if _REAL_ASYNC_QDRANT_CLIENT is not None:
    import qdrant_client
    import app.services.qdrant_client as svc_qdrant

    qdrant_client.AsyncQdrantClient = _REAL_ASYNC_QDRANT_CLIENT
    svc_qdrant.AsyncQdrantClient = _REAL_ASYNC_QDRANT_CLIENT



