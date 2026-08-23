import json
import httpx
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from app.core.config import settings
from app.database.models.enums import ImpactLevel

class GeminiAgentOutput(BaseModel):
    proposed_action: str
    action_parameters: Optional[dict[str, Any]] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: List[str]
    reason_summary: str
    financial_impact: ImpactLevel
    customer_impact: ImpactLevel

class LLMProvider:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            return "LLM API Key not provided."
        return f"Mock response from model: {self.model}"

    def generate_structured_output(self, prompt: str, allowed_actions: List[str]) -> dict:
        """
        Send a context prompt to the Gemini API, requiring strict JSON structured output.
        Validate the output structure and values against the GeminiAgentOutput Pydantic schema
        and the allowed actions list. Raises ValueError on any mismatch.
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in the environment.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }

        try:
            # Enforce strict 15-second timeout as required
            response = httpx.post(url, json=payload, headers=headers, timeout=15.0)
            response.raise_for_status()
        except httpx.TimeoutException:
            raise ValueError("Gemini API call timed out.")
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Gemini API returned error status {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise ValueError(f"Gemini API request failed: {str(e)}")

        try:
            resp_data = response.json()
            candidates = resp_data.get("candidates", [])
            if not candidates:
                raise ValueError("Gemini API returned no response candidates.")
            
            text_response = candidates[0]["content"]["parts"][0]["text"]
        except Exception as e:
            raise ValueError(f"Malformed Gemini API response layout: {str(e)}")

        try:
            raw_json = json.loads(text_response.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Gemini returned invalid JSON content: {str(e)}")

        # Validate with Pydantic
        try:
            validated = GeminiAgentOutput.model_validate(raw_json)
        except Exception as e:
            raise ValueError(f"Gemini output failed validation schema checks: {str(e)}")

        # Validate allowed actions list
        if validated.proposed_action not in allowed_actions:
            raise ValueError(
                f"Gemini proposed action '{validated.proposed_action}' "
                f"is not in the allowed actions list: {allowed_actions}"
            )

        # Validate required fields are not empty
        if not validated.evidence:
            raise ValueError("Gemini output validation failed: evidence list must not be empty.")

        if validated.confidence < 0.0 or validated.confidence > 1.0:
            raise ValueError("Gemini output validation failed: confidence must be between 0.0 and 1.0.")

        return validated.model_dump()
