import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import String, ForeignKey, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.database.models.enums import ShieldDecisionType

class ShieldDecision(Base):
    __tablename__ = "shield_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("agent_proposals.id", ondelete="CASCADE"), 
        nullable=False, 
        unique=True,
        index=True
    )
    decision: Mapped[ShieldDecisionType] = mapped_column(
        SQLEnum(ShieldDecisionType, native_enum=False), 
        nullable=False
    )
    final_action: Mapped[str] = mapped_column(String(255), nullable=False)
    final_action_parameters: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    modified_from: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    proposal: Mapped["AgentProposal"] = relationship(back_populates="shield_decision")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="decision")
