import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.database.models.enums import MerchantStatus

class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        unique=True, 
        index=True
    )
    status: Mapped[MerchantStatus] = mapped_column(
        SQLEnum(MerchantStatus, native_enum=False), 
        nullable=False, 
        default=MerchantStatus.ACTIVE
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
    customers: Mapped[list["Customer"]] = relationship(
        back_populates="merchant", 
        cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="merchant"
    )
