from pydantic import Field
from app.schemas.common import BaseSchema

class FraudPredictionRequest(BaseSchema):
    Amount: float = Field(..., description="Monetary transaction amount", ge=0.0)
    Merchant_Category: str = Field(..., description="Category of the merchant")
    Distance_from_Home: float = Field(..., description="Distance from the customer's home", ge=0.0)
    Device_Type: str = Field(..., description="Type of device used for the transaction")
    IP_Risk_Score: float = Field(..., description="Risk score associated with the IP address", ge=0.0, le=1.0)
    Avg_Spending_Habit: float = Field(..., description="Average spending habit of the customer", ge=0.0)
    Is_Weekend: int = Field(..., description="1 if weekend, 0 otherwise", ge=0, le=1)
    Is_Night_Transaction: int = Field(..., description="1 if night transaction, 0 otherwise", ge=0, le=1)
    Transaction_Hour: int = Field(..., description="Hour of the transaction (0-23)", ge=0, le=23)
    Day_of_Week: int = Field(..., description="Day of the week (0-6)", ge=0, le=6)
