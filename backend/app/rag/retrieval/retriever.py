import logging
import uuid
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database.models.policy_embedding import PolicyEmbedding
from app.rag.embeddings.provider import GeminiEmbeddingProvider
from app.rag.schemas import RetrievedPolicy

logger = logging.getLogger(__name__)

async def retrieve_relevant_policies(
    db: Session, 
    merchant_id: uuid.UUID, 
    query_text: str, 
    limit: int = 3
) -> List[RetrievedPolicy]:
    """
    Retrieves the most semantically relevant policies for a given merchant query.
    Enforces strict tenant isolation by filtering on merchant_id.
    
    Args:
        db: Database session.
        merchant_id: UUID of the merchant.
        query_text: The search query (e.g. description of transaction context).
        limit: Max number of policies to return.
        
    Returns:
        List of RetrievedPolicy ordered by similarity descending.
    """
    # Get embedding for the query using task_type='RETRIEVAL_QUERY'
    provider = GeminiEmbeddingProvider()
    try:
        query_vector = await provider.get_embedding(query_text, task_type="RETRIEVAL_QUERY")
    except Exception as e:
        logger.error(f"Failed to generate query embedding: {e}")
        return []

    # Construct pgvector cosine distance expression
    # Cosine distance = 1 - cosine_similarity. Range: [0, 2]
    distance_expr = PolicyEmbedding.embedding.cosine_distance(query_vector).label("distance")

    # Select PolicyEmbedding join/filter with MerchantPolicy for active check
    stmt = (
        select(PolicyEmbedding, distance_expr)
        .filter(PolicyEmbedding.merchant_id == merchant_id)
        .order_by(distance_expr)
        .limit(limit)
    )

    results = db.execute(stmt).all()

    retrieved = []
    for row in results:
        policy_emb, distance = row
        # Ensure we check the related policy object
        policy = policy_emb.policy
        if not policy or not policy.is_active:
            continue
            
        # Compute cosine similarity score (1 - distance)
        similarity_score = 1.0 - float(distance) if distance is not None else 0.0

        retrieved.append(
            RetrievedPolicy(
                policy_id=policy.id,
                policy_key=policy.policy_key,
                policy_name=policy.policy_name,
                description=policy.description,
                policy_value=policy.policy_value,
                similarity_score=similarity_score,
                document_content=policy_emb.document_content
            )
        )
        
    return retrieved

def retrieve_relevant_policies_sync(
    db: Session, 
    merchant_id: uuid.UUID, 
    query_text: str, 
    limit: int = 3
) -> List[RetrievedPolicy]:
    """
    Synchronous wrapper for retrieve_relevant_policies, loop-safe for worker threads.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    def run_in_new_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                retrieve_relevant_policies(db, merchant_id, query_text, limit)
            )
        finally:
            loop.close()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_in_new_loop)
        return future.result()

