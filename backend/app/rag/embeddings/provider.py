import httpx
import math
from typing import List
from app.core.config import settings

class GeminiEmbeddingProvider:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_EMBEDDING_MODEL  # e.g., gemini-embedding-001
        self.dimension = settings.GEMINI_EMBEDDING_DIM  # e.g., 768

    def _l2_normalize(self, vector: List[float]) -> List[float]:
        """Performs L2-normalization on a vector to project it onto a unit sphere."""
        norm = math.sqrt(sum(x * x for x in vector))
        if norm == 0:
            return vector
        return [x / norm for x in vector]

    async def get_embedding(self, text: str, task_type: str) -> List[float]:
        """
        Calls the Gemini API to get text embeddings with the requested task type.
        
        Args:
            text: The raw text content to embed.
            task_type: The task type, must be 'RETRIEVAL_DOCUMENT' or 'RETRIEVAL_QUERY'.
            
        Returns:
            L2-normalized float vector of length `settings.GEMINI_EMBEDDING_DIM`.
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in the environment.")

        if task_type not in ["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"]:
            raise ValueError(f"Unsupported task_type: {task_type}. Must be RETRIEVAL_DOCUMENT or RETRIEVAL_QUERY.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent?key={self.api_key}"
        
        # Build the payload, placing taskType and outputDimensionality in embedContentConfig
        payload = {
            "content": {
                "parts": [{"text": text}]
            },
            "taskType": task_type,
            "outputDimensionality": self.dimension
        }

        headers = {
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            try:
                # 15 seconds timeout
                response = await client.post(url, json=payload, headers=headers, timeout=15.0)
                response.raise_for_status()
            except httpx.TimeoutException:
                raise ValueError("Gemini Embedding API call timed out.")
            except httpx.HTTPStatusError as e:
                raise ValueError(f"Gemini Embedding API returned error status {e.response.status_code}: {e.response.text}")
            except Exception as e:
                raise ValueError(f"Gemini Embedding API request failed: {str(e)}")

        try:
            resp_data = response.json()
            embedding_data = resp_data.get("embedding", {})
            vector = embedding_data.get("values", [])
        except Exception as e:
            raise ValueError(f"Malformed Gemini Embedding API response: {str(e)}")

        if not vector:
            raise ValueError("No embedding values returned from Gemini Embedding API.")

        # Validate vector dimension
        if len(vector) != self.dimension:
            raise ValueError(
                f"Embedding vector dimension mismatch: expected {self.dimension}, got {len(vector)}."
            )

        # L2-normalize the vector
        normalized_vector = self._l2_normalize(vector)
        return normalized_vector
