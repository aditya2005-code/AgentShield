import uuid
from typing import Sequence, Optional
from sqlalchemy.orm import Session
from app.database.models.merchant import Merchant

def get_merchants(db: Session) -> Sequence[Merchant]:
    return db.query(Merchant).all()

def get_merchant_by_id(db: Session, merchant_id: uuid.UUID) -> Optional[Merchant]:
    return db.query(Merchant).filter(Merchant.id == merchant_id).first()
