import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.transaction import TransactionResponse, TransactionDetailResponse
from app.services import transaction_service

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.get("", response_model=List[TransactionResponse], summary="Retrieve list of transactions")
def read_transactions(
    merchant_id: Optional[uuid.UUID] = Query(None, description="Filter by merchant UUID"),
    customer_id: Optional[uuid.UUID] = Query(None, description="Filter by customer UUID"),
    status: Optional[str] = Query(None, description="Filter by status (PENDING, SUCCESS, FAILED, BLOCKED)"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    Fetch a list of transactions, sorted by newest first, with support for filtering and pagination.
    """
    return transaction_service.get_transactions(
        db, limit=limit, offset=offset, merchant_id=merchant_id, customer_id=customer_id, status=status
    )

@router.get("/{transaction_id}", response_model=TransactionDetailResponse, summary="Retrieve a single transaction with details")
def read_transaction(transaction_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Fetch complete details of a single transaction including related merchant, customer, and device summaries.
    """
    transaction = transaction_service.get_transaction_by_id(db, transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {transaction_id} not found"
        )
    return transaction
