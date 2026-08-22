import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.database.models.enums import AgentType, AgentStatus

class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    agent_key: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        unique=True, 
        index=True
    )
    agent_type: Mapped[AgentType] = mapped_column(
        SQLEnum(AgentType, native_enum=False), 
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[AgentStatus] = mapped_column(
        SQLEnum(AgentStatus, native_enum=False), 
        nullable=False, 
        default=AgentStatus.ACTIVE
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    proposals: Mapped[list["AgentProposal"]] = relationship(
        back_populates="agent", 
        cascade="all, delete-orphan"
    )
    permissions: Mapped[list["AgentPermission"]] = relationship(
        back_populates="agent", 
        cascade="all, delete-orphan"
    )
