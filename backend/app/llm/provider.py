import os
from typing import Optional

class LLMProvider:
    def __init__(self, api_key: Optional[str] = None, provider: str = "gemini"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.provider = provider

    def is_available(self) -> bool:
        return self.api_key is not None

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            return "LLM API Key not provided. Running in deterministic heuristic fallback mode."
        return f"Mock LLM response for: '{prompt}'"
