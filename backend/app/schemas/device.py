import uuid
from datetime import datetime
from pydantic import Field
from app.schemas.common import BaseSchema

class DeviceBase(BaseSchema):
    customer_id: uuid.UUID
    device_fingerprint: str = Field(..., max_length=255, description="Unique hardware fingerprint")
    device_type: str = Field(..., max_length=100, description="Device browser/operating system/type")
    is_trusted: bool = False
    first_seen_at: datetime
    last_seen_at: datetime

class DeviceCreate(DeviceBase):
    pass

class DeviceResponse(DeviceBase):
    id: uuid.UUID

class DeviceSummary(BaseSchema):
    id: uuid.UUID
    device_fingerprint: str
    device_type: str
