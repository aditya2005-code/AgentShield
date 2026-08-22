import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import Field
from app.database.models.enums import AuditEventType
from app.schemas.common import BaseSchema

class AuditLogBase(BaseSchema):
    merchant_id: Optional[uuid.UUID] = None
    agent_id: Optional[uuid.UUID] = None
    proposal_id: Optional[uuid.UUID] = None
    decision_id: Optional[uuid.UUID] = None
    event_type: AuditEventType
    action: str = Field(..., max_length=255)
    details: dict[str, Any]

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogResponse(AuditLogBase):
    id: uuid.UUID
    created_at: datetime
