import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, ForeignKey, DateTime, Numeric, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.database.models.enums import TransactionStatus

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    external_transaction_id: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        unique=True, 
        index=True
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("merchants.id", ondelete="RESTRICT"), 
        nullable=False, 
        index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("customers.id", ondelete="RESTRICT"), 
        nullable=False, 
        index=True
    )
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("devices.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True
    )
    
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    payment_method: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(
        SQLEnum(TransactionStatus, native_enum=False), 
        nullable=False, 
        default=TransactionStatus.PENDING
    )
    
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    merchant: Mapped["Merchant"] = relationship(back_populates="transactions")
    customer: Mapped["Customer"] = relationship(back_populates="transactions")
    device: Mapped[Optional["Device"]] = relationship(back_populates="transactions")
