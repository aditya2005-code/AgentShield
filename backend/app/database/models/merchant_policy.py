import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import String, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class MerchantPolicy(Base):
    __tablename__ = "merchant_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("merchants.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    policy_key: Mapped[str] = mapped_column(String(100), nullable=False)
    policy_name: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

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

    __table_args__ = (
        UniqueConstraint(
            "merchant_id", 
            "policy_key", 
            name="uq_merchant_policy_key"
        ),
    )

    # Relationships
    merchant: Mapped["Merchant"] = relationship(back_populates="policies")
