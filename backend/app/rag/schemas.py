from dataclasses import dataclass
from typing import Optional, Any
import uuid

@dataclass
class RetrievedPolicy:
    policy_id: uuid.UUID
    policy_key: str
    policy_name: str
    description: Optional[str]
    policy_value: dict[str, Any]
    similarity_score: float
    document_content: str
