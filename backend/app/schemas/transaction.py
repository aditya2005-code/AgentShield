import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import Field
from app.database.models.enums import TransactionStatus
from app.schemas.common import BaseSchema

class TransactionBase(BaseSchema):
    external_transaction_id: str = Field(..., max_length=255, description="Client-facing transaction ID")
    merchant_id: uuid.UUID
    customer_id: uuid.UUID
    device_id: Optional[uuid.UUID] = None
    amount: Decimal = Field(..., description="Monetary transaction amount (Precise Decimal)")
    currency: str = Field("INR", max_length=10)
    payment_method: str = Field(..., max_length=100)
    location: str = Field(..., max_length=255)
    status: TransactionStatus = TransactionStatus.PENDING
    occurred_at: datetime

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: uuid.UUID
    created_at: datetime
