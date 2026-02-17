import sys
import os
sys.path.append(os.getcwd())
from app.config import settings
print(f"DEBUG: GROQ_API_KEY={settings.groq_api_key}")
print(f"DEBUG: QDRANT_URL={settings.qdrant_url}")
print(f"DEBUG: CWD={os.getcwd()}")
print(f"DEBUG: .env exists here: {os.path.exists('.env')}")
