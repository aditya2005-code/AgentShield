import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.database.models.merchant import Merchant
from app.database.models.merchant_policy import MerchantPolicy
from app.database.models.policy_embedding import PolicyEmbedding
from app.database.models.transaction import Transaction
from app.database.models.customer import Customer
from app.database.models.agent_proposal import AgentProposal
from app.database.models.audit_log import AuditLog
from app.database.models.enums import TransactionStatus, ProposalStatus
from app.rag import normalize_policy_to_text, index_policy
from app.rag.embeddings.provider import GeminiEmbeddingProvider

client = TestClient(app)

def test_normalize_policy_to_text():
    policy = MerchantPolicy(
        policy_name="Test Policy Rules",
        policy_key="test_policy",
        description="A policy for testing normalization",
        policy_value={
            "max_limit": 500,
            "allowed_methods": ["card", "paypal"],
            "details": {"nested_key": "nested_val"}
        }
    )
    text = normalize_policy_to_text(policy)
    
    assert "Policy Name: Test Policy Rules" in text
    assert "Policy Key: test_policy" in text
    assert "Description: A policy for testing normalization" in text
    assert "max_limit: 500" in text
    assert "allowed_methods: [card, paypal]" in text
    assert "nested_key: nested_val" in text

@pytest.mark.anyio
async def test_embedding_provider_dimension_validation():
    # Test that the provider raises ValueError if the API returns wrong dimension
    provider = GeminiEmbeddingProvider()
    
    # 1. Incorrect dimension validation
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Return 3 elements instead of 768
        mock_response.json.return_value = {"embedding": {"values": [0.1, 0.2, 0.3]}}
        mock_post.return_value = mock_response
        
        with pytest.raises(ValueError, match="Embedding vector dimension mismatch"):
            await provider.get_embedding("hello", "RETRIEVAL_DOCUMENT")

@pytest.mark.anyio
@patch("app.rag.embeddings.provider.GeminiEmbeddingProvider.get_embedding", new_callable=AsyncMock)
async def test_rag_indexing_lifecycle_and_isolation(mock_get_embedding):
    dummy_vector = [0.1] * 768
    norm = sum(x*x for x in dummy_vector) ** 0.5
    normalized_dummy_vector = [x / norm for x in dummy_vector]
    mock_get_embedding.return_value = normalized_dummy_vector

    db = SessionLocal()
    try:
        # Fetch ScribeFlow merchant (Merchant A)
        merchant_a = db.query(Merchant).filter(Merchant.slug == "scribeflow-premium").first()
        # Fetch NovaPixel merchant (Merchant B)
        merchant_b = db.query(Merchant).filter(Merchant.slug == "novapixel-assets").first()
        
        assert merchant_a is not None
        assert merchant_b is not None

        # 1. Indexing active policies
        policy_a = MerchantPolicy(
            merchant_id=merchant_a.id,
            policy_key="rag_test_policy_a",
            policy_name="Merchant A Max Discount",
            policy_value={"max_discount_percent": 10},
            description="Discount policy for Merchant A",
            is_active=True
        )
        policy_b = MerchantPolicy(
            merchant_id=merchant_b.id,
            policy_key="rag_test_policy_b",
            policy_name="Merchant B Max Discount",
            policy_value={"max_discount_percent": 30},
            description="Discount policy for Merchant B",
            is_active=True
        )
        db.add(policy_a)
        db.add(policy_b)
        db.commit()

        # Index policy_a
        emb_a1 = await index_policy(db, policy_a)
        assert emb_a1 is not None
        assert emb_a1.merchant_id == merchant_a.id
        
        # 2. Re-indexing without duplicate rows
        emb_a2 = await index_policy(db, policy_a)
        assert emb_a2 is not None
        assert emb_a2.id == emb_a1.id  # Same primary key, updated in-place

        # Assert database contains exactly 1 row for policy_a
        rows = db.query(PolicyEmbedding).filter_by(policy_id=policy_a.id).all()
        assert len(rows) == 1

        # Index policy_b
        await index_policy(db, policy_b)

        # 3. Strict Merchant A / Merchant B isolation
        query_payload = {"query_text": "discount limits", "limit": 5}
        
        # Query Merchant A's RAG space
        response_a = client.post(f"/api/v1/rag/merchants/{merchant_a.id}/query", json=query_payload)
        assert response_a.status_code == 200
        results_a = response_a.json()
        
        # Verify Merchant B's policy (with max_discount_percent=30) never appears
        policy_keys_a = [r["policy_key"] for r in results_a]
        assert "rag_test_policy_a" in policy_keys_a
        assert "rag_test_policy_b" not in policy_keys_a

        # Query Merchant B's RAG space
        response_b = client.post(f"/api/v1/rag/merchants/{merchant_b.id}/query", json=query_payload)
        assert response_b.status_code == 200
        results_b = response_b.json()
        policy_keys_b = [r["policy_key"] for r in results_b]
        assert "rag_test_policy_b" in policy_keys_b
        assert "rag_test_policy_a" not in policy_keys_b

        # 4. Inactive policy exclusion & deletion
        policy_a.is_active = False
        db.commit()
        
        # Re-indexing an inactive policy should remove its embedding from the DB
        await index_policy(db, policy_a)
        emb_inactive = db.query(PolicyEmbedding).filter_by(policy_id=policy_a.id).first()
        assert emb_inactive is None

        # Empty retrieval: query Merchant A space, should return empty
        response_empty = client.post(f"/api/v1/rag/merchants/{merchant_a.id}/query", json=query_payload)
        assert response_empty.status_code == 200
        assert len(response_empty.json()) == 0

    finally:
        # Cleanup
        db.query(PolicyEmbedding).filter(PolicyEmbedding.policy_id.in_([policy_a.id, policy_b.id])).delete(synchronize_session=False)
        db.query(MerchantPolicy).filter(MerchantPolicy.policy_key.like("rag_test_policy_%")).delete(synchronize_session=False)
        db.commit()
        db.close()

@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.rag.retrieval.retrieve_relevant_policies_sync")
def test_agents_rag_prompt_integration(mock_retrieve, mock_llm_generate):
    """
    Verifies that both Recovery and Growth agents:
    1. Call retrieve_relevant_policies_sync with correct merchant_id and contextual query
    2. Inject retrieved policy text into the LLM prompt
    """
    from app.rag.schemas import RetrievedPolicy
    mock_policy = RetrievedPolicy(
        policy_id=uuid.uuid4(),
        policy_key="test_recovery_limit",
        policy_name="Test Recovery Limit Policy",
        description="Limits retries",
        policy_value={"max_retries": 2},
        similarity_score=0.92,
        document_content="Policy Name: Test Recovery Limit Policy\nRules: max_retries=2"
    )
    mock_retrieve.return_value = [mock_policy]
    
    mock_llm_generate.return_value = {
        "proposed_action": "WAIT_AND_RETRY",
        "action_parameters": {"wait_hours": 12},
        "confidence": 0.90,
        "evidence": ["RETRY_POLICY_LIMIT"],
        "reason_summary": "Retrying based on merchant policy guidelines.",
        "financial_impact": "LOW",
        "customer_impact": "LOW"
    }

    db = SessionLocal()
    recovery_prop_id = None
    growth_prop_id = None
    try:
        # --- Recovery Agent ---
        tx = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_302").first()
        assert tx is not None

        # Clean up any existing PENDING proposals for this tx to bypass idempotency guard
        db.query(AuditLog).filter(AuditLog.proposal_id.in_(
            db.query(AgentProposal.id).filter(
                AgentProposal.event_id == str(tx.id),
                AgentProposal.status == ProposalStatus.PENDING
            )
        )).delete(synchronize_session=False)
        db.query(AgentProposal).filter(
            AgentProposal.event_id == str(tx.id),
            AgentProposal.status == ProposalStatus.PENDING
        ).delete(synchronize_session=False)
        db.commit()
        
        response = client.post("/api/v1/agents/recovery/execute", json={"transaction_id": str(tx.id)})
        assert response.status_code == 201
        recovery_prop_id = response.json().get("proposal_id")
        
        # Verify retrieve_relevant_policies_sync was called for recovery
        assert mock_retrieve.call_count == 1
        args_rec, _ = mock_retrieve.call_args
        assert args_rec[1] == tx.merchant_id
        assert "Payment failure:" in args_rec[2]

        # Verify LLM prompt includes the retrieved policy text
        llm_prompt = mock_llm_generate.call_args[0][0]
        assert "Retrieved Merchant Policies" in llm_prompt
        assert "Test Recovery Limit Policy" in llm_prompt
        assert "max_retries=2" in llm_prompt

        # Reset for Growth Agent test
        mock_retrieve.reset_mock()
        mock_llm_generate.reset_mock()
        
        # --- Growth Agent ---
        customer = db.query(Customer).filter(Customer.external_customer_id == "cust_sf_001").first()
        sf = db.query(Merchant).filter(Merchant.slug == "scribeflow-premium").first()
        assert customer is not None
        assert sf is not None

        # Clean up any existing PENDING growth proposals for this customer
        db.query(AuditLog).filter(AuditLog.proposal_id.in_(
            db.query(AgentProposal.id).filter(
                AgentProposal.event_id == str(customer.id),
                AgentProposal.event_type == "GROWTH_OPPORTUNITY",
                AgentProposal.status == ProposalStatus.PENDING
            )
        )).delete(synchronize_session=False)
        db.query(AgentProposal).filter(
            AgentProposal.event_id == str(customer.id),
            AgentProposal.event_type == "GROWTH_OPPORTUNITY",
            AgentProposal.status == ProposalStatus.PENDING
        ).delete(synchronize_session=False)
        db.commit()

        mock_llm_generate.return_value = {
            "proposed_action": "APPLY_DISCOUNT",
            "action_parameters": {"discount_percent": 10},
            "confidence": 0.88,
            "evidence": ["GROWTH_POLICY"],
            "reason_summary": "Discount applied.",
            "financial_impact": "LOW",
            "customer_impact": "LOW"
        }

        response = client.post("/api/v1/agents/growth/execute", json={
            "merchant_id": str(sf.id),
            "customer_id": str(customer.id)
        })
        assert response.status_code == 201
        growth_prop_id = response.json().get("proposal_id")

        # Verify retriever called once for growth
        assert mock_retrieve.call_count == 1
        args_growth, _ = mock_retrieve.call_args
        assert args_growth[1] == sf.id
        assert "Growth opportunity:" in args_growth[2]

        llm_prompt = mock_llm_generate.call_args[0][0]
        assert "Retrieved Merchant Policies" in llm_prompt
        assert "Test Recovery Limit Policy" in llm_prompt

    finally:
        # Clean up proposals created by this test
        if recovery_prop_id:
            db.query(AuditLog).filter(AuditLog.proposal_id == recovery_prop_id).delete(synchronize_session=False)
            db.query(AgentProposal).filter(AgentProposal.id == recovery_prop_id).delete(synchronize_session=False)
        if growth_prop_id:
            db.query(AuditLog).filter(AuditLog.proposal_id == growth_prop_id).delete(synchronize_session=False)
            db.query(AgentProposal).filter(AgentProposal.id == growth_prop_id).delete(synchronize_session=False)
        db.commit()
        db.close()

@patch("app.rag.embeddings.provider.GeminiEmbeddingProvider.get_embedding", new_callable=AsyncMock)
def test_controlled_embedding_failure_indexing(mock_get_embedding):
    """
    Verifies that a Gemini embedding API failure during indexing
    propagates as a controlled 500 error from the index endpoint.
    We must have at least one active policy for the merchant so that
    the indexer actually calls get_embedding (otherwise it returns 0 with 200).
    """
    mock_get_embedding.side_effect = ValueError("Gemini Embedding API call timed out.")
    
    db = SessionLocal()
    try:
        sf = db.query(Merchant).filter(Merchant.slug == "scribeflow-premium").first()
        assert sf is not None

        # Create a temporary active policy so indexer has something to embed
        temp_policy = MerchantPolicy(
            merchant_id=sf.id,
            policy_key="rag_failure_test_policy",
            policy_name="Failure Test Policy",
            policy_value={"test": True},
            description="Temporary policy for failure test",
            is_active=True
        )
        db.add(temp_policy)
        db.commit()

        response = client.post(f"/api/v1/rag/merchants/{sf.id}/index")
        assert response.status_code == 500
        assert "RAG indexing failed" in response.json()["detail"]

    finally:
        # Clean up the temp policy
        db.query(MerchantPolicy).filter(
            MerchantPolicy.policy_key == "rag_failure_test_policy"
        ).delete(synchronize_session=False)
        db.commit()
        db.close()

@patch("app.rag.embeddings.provider.GeminiEmbeddingProvider.get_embedding", new_callable=AsyncMock)
def test_controlled_embedding_failure_retrieval(mock_get_embedding):
    """
    Verifies that a Gemini embedding API failure during retrieval query
    is handled gracefully. The retriever catches the error and returns
    an empty result list, so the query endpoint returns 200 with [].
    """
    mock_get_embedding.side_effect = ValueError("Gemini Embedding API call timed out.")
    
    db = SessionLocal()
    try:
        sf = db.query(Merchant).filter(Merchant.slug == "scribeflow-premium").first()
        assert sf is not None

        response_query = client.post(
            f"/api/v1/rag/merchants/{sf.id}/query", 
            json={"query_text": "any query"}
        )
        # Retriever catches embedding error and returns [], so endpoint returns 200 with empty list
        assert response_query.status_code == 200
        assert response_query.json() == []

    finally:
        db.close()
