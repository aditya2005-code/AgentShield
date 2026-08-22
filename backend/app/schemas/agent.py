import uuid
from datetime import datetime
from typing import Optional
from pydantic import Field
from app.database.models.enums import AgentType, AgentStatus
from app.schemas.common import BaseSchema

class AgentBase(BaseSchema):
    agent_key: str = Field(..., max_length=255, description="Unique alphanumeric key identifying the agent")
    agent_type: AgentType = Field(..., description="The functional type/class of the agent")
    name: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    status: AgentStatus = AgentStatus.ACTIVE

class AgentCreate(AgentBase):
    pass

class AgentResponse(AgentBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

class AgentSummary(BaseSchema):
    id: uuid.UUID
    agent_key: str
    agent_type: AgentType
    name: str
