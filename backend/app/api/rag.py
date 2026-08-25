import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.rag import index_merchant_policies, retrieve_relevant_policies

router = APIRouter(prefix="/rag", tags=["RAG / Policy Search"])

class RAGIndexResponse(BaseModel):
    merchant_id: uuid.UUID
    indexed_count: int
    message: str

class RAGQueryRequest(BaseModel):
    query_text: str
    limit: Optional[int] = 3

class RetrievedPolicyResponse(BaseModel):
    policy_id: uuid.UUID
    policy_key: str
    policy_name: str
    description: Optional[str] = None
    similarity_score: float
    document_content: str

@router.post("/merchants/{merchant_id}/index", response_model=RAGIndexResponse, summary="Build or update vector index for all merchant policies")
async def index_policies(merchant_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Triggers embedding generation and vector database indexing for all active
    policies belonging to the specified merchant.
    """
    try:
        count = await index_merchant_policies(db, merchant_id)
        return RAGIndexResponse(
            merchant_id=merchant_id,
            indexed_count=count,
            message=f"Successfully indexed/updated {count} policy embeddings."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG indexing failed: {str(e)}"
        )

@router.post("/merchants/{merchant_id}/query", response_model=List[RetrievedPolicyResponse], summary="Perform vector search across merchant policies")
async def query_policies(
    merchant_id: uuid.UUID, 
    payload: RAGQueryRequest, 
    db: Session = Depends(get_db)
):
    """
    Retrieves the most semantically relevant policy documents for a given query text.
    Enforces strict tenant isolation by scope-filtering to the requested merchant.
    """
    try:
        results = await retrieve_relevant_policies(
            db=db,
            merchant_id=merchant_id,
            query_text=payload.query_text,
            limit=payload.limit
        )
        return [
            RetrievedPolicyResponse(
                policy_id=r.policy_id,
                policy_key=r.policy_key,
                policy_name=r.policy_name,
                description=r.description,
                similarity_score=r.similarity_score,
                document_content=r.document_content
            )
            for r in results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG retrieval query failed: {str(e)}"
        )
