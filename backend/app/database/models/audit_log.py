import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import String, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.database.models.enums import AuditEventType

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    merchant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("merchants.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True
    )
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("agents.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True
    )
    proposal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("agent_proposals.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True
    )
    decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("shield_decisions.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True
    )
    event_type: Mapped[AuditEventType] = mapped_column(
        SQLEnum(AuditEventType, native_enum=False), 
        nullable=False
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    merchant: Mapped[Optional["Merchant"]] = relationship(back_populates="audit_logs")
    proposal: Mapped[Optional["AgentProposal"]] = relationship(back_populates="audit_logs")
    decision: Mapped[Optional["ShieldDecision"]] = relationship(back_populates="audit_logs")
