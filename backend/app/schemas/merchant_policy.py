import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import Field
from app.schemas.common import BaseSchema

class MerchantPolicyBase(BaseSchema):
    merchant_id: uuid.UUID
    policy_key: str = Field(..., max_length=100)
    policy_name: str = Field(..., max_length=255)
    policy_value: dict[str, Any]
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = True

class MerchantPolicyCreate(MerchantPolicyBase):
    pass

class MerchantPolicyResponse(MerchantPolicyBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
