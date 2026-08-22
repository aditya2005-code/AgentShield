import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.database.models.enums import RiskProfile

class Customer(Base):
    __tablename__ = "customers"

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
    external_customer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    risk_profile: Mapped[RiskProfile] = mapped_column(
        SQLEnum(RiskProfile, native_enum=False), 
        nullable=False, 
        default=RiskProfile.LOW
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

    __table_args__ = (
        UniqueConstraint(
            "merchant_id", 
            "external_customer_id", 
            name="uq_customer_merchant_external_id"
        ),
    )

    # Relationships
    merchant: Mapped["Merchant"] = relationship(back_populates="customers")
    devices: Mapped[list["Device"]] = relationship(
        back_populates="customer", 
        cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="customer"
    )
