import uuid
from datetime import datetime
from pydantic import Field
from app.database.models.enums import RiskProfile
from app.schemas.common import BaseSchema

class CustomerBase(BaseSchema):
    merchant_id: uuid.UUID
    external_customer_id: str = Field(..., max_length=255, description="Client-facing custom customer ID")
    email: str = Field(..., max_length=255, description="Customer contact email address")
    full_name: str = Field(..., max_length=255, description="Full name of customer")
    account_created_at: datetime
    risk_profile: RiskProfile = RiskProfile.LOW

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

class CustomerSummary(BaseSchema):
    id: uuid.UUID
    external_customer_id: str
    email: str
    full_name: str
