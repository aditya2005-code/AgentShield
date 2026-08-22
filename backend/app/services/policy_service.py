import uuid
from typing import Sequence, Optional
from sqlalchemy.orm import Session
from app.database.models.merchant_policy import MerchantPolicy

def get_merchant_policies(db: Session, merchant_id: uuid.UUID) -> Sequence[MerchantPolicy]:
    return db.query(MerchantPolicy).filter(MerchantPolicy.merchant_id == merchant_id).all()

def get_policy_by_id(db: Session, policy_id: uuid.UUID) -> Optional[MerchantPolicy]:
    return db.query(MerchantPolicy).filter(MerchantPolicy.id == policy_id).first()
