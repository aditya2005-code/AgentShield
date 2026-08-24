import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

from app.core.config import settings

# Embedding dimension matches the Gemini embedding model configuration
EMBEDDING_DIM = getattr(settings, "GEMINI_EMBEDDING_DIM", 768)

from pgvector.sqlalchemy import Vector


class PolicyEmbedding(Base):
    __tablename__ = "policy_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchant_policies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    # Denormalized for fast tenant-scoped vector search without join
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    document_content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[list]] = mapped_column(
        Vector(EMBEDDING_DIM),
        nullable=True,
    )
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)

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

    # Relationship
    policy: Mapped["MerchantPolicy"] = relationship("MerchantPolicy")
