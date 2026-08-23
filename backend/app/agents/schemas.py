import uuid
from pydantic import BaseModel

class FraudExecutionRequest(BaseModel):
    transaction_id: uuid.UUID

class RecoveryExecutionRequest(BaseModel):
    transaction_id: uuid.UUID

class GrowthExecutionRequest(BaseModel):
    merchant_id: uuid.UUID
    customer_id: uuid.UUID
