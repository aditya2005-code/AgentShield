import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Any
from sqlalchemy import String, ForeignKey, DateTime, Numeric, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.database.models.enums import ImpactLevel, ProposalStatus

class AgentProposal(Base):
    __tablename__ = "agent_proposals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("agents.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("merchants.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    action_parameters: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    
    financial_impact: Mapped[ImpactLevel] = mapped_column(
        SQLEnum(ImpactLevel, native_enum=False), 
        nullable=False
    )
    customer_impact: Mapped[ImpactLevel] = mapped_column(
        SQLEnum(ImpactLevel, native_enum=False), 
        nullable=False
    )
    
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    reason_summary: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[ProposalStatus] = mapped_column(
        SQLEnum(ProposalStatus, native_enum=False), 
        nullable=False, 
        default=ProposalStatus.PENDING
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
    agent: Mapped["Agent"] = relationship(back_populates="proposals")
    merchant: Mapped["Merchant"] = relationship(back_populates="proposals")
    shield_decision: Mapped[Optional["ShieldDecision"]] = relationship(
        back_populates="proposal", 
        cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="proposal"
    )
