import httpx, os
from pathlib import Path

for line in Path(".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

api_key = os.environ["GEMINI_API_KEY"]
r = httpx.get(
    f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
    timeout=15
)
models = r.json().get("models", [])
print("Available flash/pro models:")
for m in models:
    name = m["name"]
    methods = m.get("supportedGenerationMethods", [])
    if ("flash" in name.lower() or "pro" in name.lower()) and "generateContent" in methods:
        print(f"  {name}")
