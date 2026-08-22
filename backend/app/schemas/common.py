from pydantic import BaseModel, ConfigDict

class BaseSchema(BaseModel):
    """
    Common base schema for Pydantic models.
    Enables ORM mode by default for SQLAlchemy model compatibility.
    """
    model_config = ConfigDict(from_attributes=True)
