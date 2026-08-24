import logging
import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from app.database.models.merchant_policy import MerchantPolicy
from app.database.models.policy_embedding import PolicyEmbedding
from app.rag.embeddings.provider import GeminiEmbeddingProvider
from app.rag.policy_documents import normalize_policy_to_text

logger = logging.getLogger(__name__)

async def index_policy(db: Session, policy: MerchantPolicy) -> Optional[PolicyEmbedding]:
    """
    Generates an embedding for a MerchantPolicy and stores/updates it in policy_embeddings.
    If the policy is inactive, removes its embedding if it exists.
    """
    if not policy.is_active:
        existing = db.query(PolicyEmbedding).filter_by(policy_id=policy.id).first()
        if existing:
            db.delete(existing)
            db.commit()
            logger.info(f"Deleted embedding for inactive policy: {policy.id}")
        return None

    # Transform policy into normalized text content
    document_content = normalize_policy_to_text(policy)
    
    # Get vector embedding with taskType='RETRIEVAL_DOCUMENT'
    provider = GeminiEmbeddingProvider()
    vector = await provider.get_embedding(document_content, task_type="RETRIEVAL_DOCUMENT")

    # Upsert into policy_embeddings table
    embedding_row = db.query(PolicyEmbedding).filter_by(policy_id=policy.id).first()
    if embedding_row:
        embedding_row.document_content = document_content
        embedding_row.embedding = vector
        embedding_row.embedding_model = provider.model
    else:
        embedding_row = PolicyEmbedding(
            policy_id=policy.id,
            merchant_id=policy.merchant_id,
            document_content=document_content,
            embedding=vector,
            embedding_model=provider.model
        )
        db.add(embedding_row)
        
    db.commit()
    db.refresh(embedding_row)
    logger.info(f"Indexed policy {policy.id} successfully.")
    return embedding_row

async def index_merchant_policies(db: Session, merchant_id: uuid.UUID) -> int:
    """
    Indexes all active policies for the specified merchant.
    Deletes any embeddings for policies that are no longer active or have been deleted.
    
    Returns:
        The count of indexed policy embeddings.
    """
    # Fetch all policies for the merchant
    policies = db.query(MerchantPolicy).filter_by(merchant_id=merchant_id).all()
    
    indexed_count = 0
    policy_ids_seen = set()
    
    for policy in policies:
        if policy.is_active:
            await index_policy(db, policy)
            indexed_count += 1
            policy_ids_seen.add(policy.id)
            
    # Delete embeddings for any policy of this merchant that is NOT active or missing
    all_embeddings = db.query(PolicyEmbedding).filter_by(merchant_id=merchant_id).all()
    for emb in all_embeddings:
        if emb.policy_id not in policy_ids_seen:
            db.delete(emb)
            logger.info(f"Cleaned up stale embedding for policy {emb.policy_id}")
            
    db.commit()
    return indexed_count
