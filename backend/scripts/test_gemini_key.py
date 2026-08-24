"""
Quick smoke test for the Gemini API key.
Run from backend/ directory: python scripts/test_gemini_key.py
"""
import os
import sys
from pathlib import Path

# Load .env manually without dotenv dependency
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

api_key = os.environ.get("GEMINI_API_KEY", "")
model   = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

if not api_key:
    print("ERROR: GEMINI_API_KEY is not set in .env")
    sys.exit(1)

masked = api_key[:8] + "*" * max(0, len(api_key) - 8)
print(f"Key loaded : {masked}")
print(f"Model      : {model}")
print("Sending test request to Gemini ...")

import httpx, json

url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
payload = {
    "contents": [{"parts": [{"text": "Reply with exactly: GEMINI_OK"}]}],
    "generationConfig": {"responseMimeType": "application/json"}
}

try:
    resp = httpx.post(url, json=payload, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    print(f"SUCCESS: Gemini responded: {text.strip()}")
except httpx.HTTPStatusError as e:
    print(f"FAILED HTTP {e.response.status_code}: {e.response.text[:300]}")
    sys.exit(1)
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
