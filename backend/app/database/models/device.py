import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("customers.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    device_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[str] = mapped_column(String(100), nullable=False)
    is_trusted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "customer_id", 
            "device_fingerprint", 
            name="uq_device_customer_fingerprint"
        ),
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="devices")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="device")
