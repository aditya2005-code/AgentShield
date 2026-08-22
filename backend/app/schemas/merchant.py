import uuid
from datetime import datetime
from pydantic import Field
from app.database.models.enums import MerchantStatus
from app.schemas.common import BaseSchema

class MerchantBase(BaseSchema):
    name: str = Field(..., max_length=255, description="Name of the merchant")
    slug: str = Field(..., max_length=255, description="Unique URL slug identifier")
    status: MerchantStatus = MerchantStatus.ACTIVE

class MerchantCreate(MerchantBase):
    pass

class MerchantResponse(MerchantBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
