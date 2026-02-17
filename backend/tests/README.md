# Backend Tests

## API Key Test Script

The `test_api_keys.py` script comprehensively tests all external service integrations.

### Usage

```bash
# From backend directory
cd backend
conda activate agora  # or your Python environment
python tests/test_api_keys.py
```

### What It Tests

1. **Configuration Loading**
   - Verifies all required API keys are present
   - Checks Qdrant URL configuration
   - Validates provider settings

2. **Gemini API**
   - Client initialization
   - Health check (simple text generation)
   - Text generation with a test prompt
   - Embedding generation

3. **Qdrant Vector Database**
   - Connection to Qdrant server
   - Health check (collection listing)
   - Collection access verification

4. **Deepgram STT**
   - Client initialization
   - Service readiness (skips actual transcription test)

5. **ElevenLabs TTS**
   - Client initialization
   - Audio synthesis with test text
   - Verifies audio data is generated

### Output

The script provides colored terminal output:
- ✅ Green checkmarks for successful tests
- ✗ Red X marks for failed tests
- ⚠ Yellow warnings for skipped tests
- ℹ Blue info messages for status updates

### Example Output

```
================================================================================
                    Agora API Keys & Services Test Suite
================================================================================

ℹ Starting comprehensive service tests...
ℹ This will test: Gemini, Qdrant, Deepgram, ElevenLabs

================================================================================
                        Testing Configuration
================================================================================

ℹ Checking API keys...
✓ Gemini API key: AIzaSyC...
✓ Deepgram API key: abc123...
✓ ElevenLabs API key: xyz789...
✓ Qdrant URL configured

================================================================================
                          Testing Gemini API
================================================================================

ℹ Initializing Gemini client...
✓ Gemini client initialized
✓ Gemini health check passed
✓ Text generation works: OK
✓ Embedding generated: 768 dimensions
✓ Gemini API test completed successfully

...

================================================================================
                            Test Summary
================================================================================

✓ CONFIGURATION: PASSED
✓ GEMINI: PASSED
✓ QDRANT: PASSED
✓ DEEPGRAM: PASSED
✓ ELEVENLABS: PASSED

Total: 5/5 tests passed
✓ All tests passed! Your backend is ready.
```

### Troubleshooting

**If Gemini test fails:**
- Check `GEMINI_API` environment variable
- Verify API key is valid and has quota
- Check internet connection

**If Qdrant test fails:**
- Ensure Qdrant is running: `docker-compose up -d` or local install
- Check `QDRANT_URL` in .env (default: http://localhost:6333)
- Verify Qdrant is accessible at the URL

**If Deepgram test fails:**
- Check `DEEPGRAM_API` environment variable
- Verify API key is valid

**If ElevenLabs test fails:**
- Check `ELEVEN_API` environment variable
- Verify API key is valid and has quota
- Check internet connection

### Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed

This makes it suitable for CI/CD pipelines.

