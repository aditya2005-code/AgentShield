from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.session import get_db
from pydantic import BaseModel

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    database: str
    day: int

@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    db_status = "disconnected"
    try:
        # Verify connection by executing a fast dummy query
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        # Do not log or expose the connection exception string directly
        pass

    overall_status = "healthy" if db_status == "connected" else "unhealthy"

    return HealthResponse(
        status=overall_status,
        database=db_status,
        day=2
    )
