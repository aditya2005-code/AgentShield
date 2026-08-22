import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.merchant import MerchantResponse
from app.schemas.merchant_policy import MerchantPolicyResponse
from app.services import merchant_service, policy_service

router = APIRouter(prefix="/merchants", tags=["Merchants"])

@router.get("", response_model=List[MerchantResponse], summary="Retrieve all merchants")
def read_merchants(db: Session = Depends(get_db)):
    """
    Fetch all merchants registered on the platform.
    """
    return merchant_service.get_merchants(db)

@router.get("/{merchant_id}", response_model=MerchantResponse, summary="Retrieve a single merchant by ID")
def read_merchant(merchant_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Fetch details of a single merchant by its unique UUID.
    """
    merchant = merchant_service.get_merchant_by_id(db, merchant_id)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant with ID {merchant_id} not found"
        )
    return merchant

@router.get("/{merchant_id}/policies", response_model=List[MerchantPolicyResponse], summary="Retrieve policies for a merchant")
def read_merchant_policies(merchant_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Fetch all policies configured for a specific merchant.
    """
    merchant = merchant_service.get_merchant_by_id(db, merchant_id)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant with ID {merchant_id} not found"
        )
    return policy_service.get_merchant_policies(db, merchant_id)
