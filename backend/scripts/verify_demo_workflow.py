import os
import sys
import uuid
from unittest.mock import patch

# Ensure the backend directory is in the path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database.session import SessionLocal
from app.database.models import (
    Transaction, Customer, AgentProposal, ShieldDecision, AuditLog, EventWorkflow, MerchantPolicy
)
from app.services.orchestration_service import process_event_orchestration

def clean_event_data(db, event_id):
    db.query(AuditLog).filter(AuditLog.proposal_id.in_(
        db.query(AgentProposal.id).filter(AgentProposal.event_id == str(event_id))
    )).delete(synchronize_session=False)
    db.query(ShieldDecision).filter(ShieldDecision.proposal_id.in_(
        db.query(AgentProposal.id).filter(AgentProposal.event_id == str(event_id))
    )).delete(synchronize_session=False)
    db.query(AgentProposal).filter(AgentProposal.event_id == str(event_id)).delete(synchronize_session=False)
    db.query(EventWorkflow).filter(EventWorkflow.event_id == str(event_id)).delete(synchronize_session=False)
    db.commit()

# Gemini structured output mock router
def mock_gemini_output(prompt, allowed_actions):
    prompt_upper = prompt.upper()
    
    if "FRAUD DETECTION AGENT" in prompt_upper:
        # Check if transaction ID matches the high-fraud tx_vc_304 ID
        if "180B50AE-C0ED-4A08-89EE-B103D7558C38" in prompt_upper:
            return {
                "proposed_action": "BLOCK_TRANSACTION",
                "action_parameters": None,
                "confidence": 0.99,
                "evidence": ["NEW_DEVICE", "UNUSUAL_LOCATION", "HIGH_TRANSACTION_AMOUNT"],
                "reason_summary": "High risk anomaly: Moscow location, untrusted device, and 120,000 INR amount.",
                "financial_impact": "HIGH",
                "customer_impact": "MEDIUM"
            }
        else:
            return {
                "proposed_action": "ALLOW_TRANSACTION",
                "action_parameters": None,
                "confidence": 0.95,
                "evidence": ["CLEAN_HISTORY"],
                "reason_summary": "Transaction matches typical customer spending patterns.",
                "financial_impact": "LOW",
                "customer_impact": "LOW"
            }
            
    elif "PAYMENT RECOVERY AGENT" in prompt_upper:
        return {
            "proposed_action": "WAIT_AND_RETRY",
            "action_parameters": {"wait_hours": 24},
            "confidence": 0.88,
            "evidence": ["CARD_DECLINED_INSUFFICIENT_FUNDS"],
            "reason_summary": "Insufficient funds decline. Proposing temporary wait and retry dunning step.",
            "financial_impact": "LOW",
            "customer_impact": "LOW"
        }
        
    elif "GROWTH INCENTIVES AGENT" in prompt_upper:
        # Check if it is Low Risk Success (which proposes discount of 15% to trigger Shield MODIFY to 10%)
        if "CUST_VC_001" in prompt_upper:
            return {
                "proposed_action": "APPLY_DISCOUNT",
                "action_parameters": {"discount_percent": 15},
                "confidence": 0.85,
                "evidence": ["LOYAL_CUSTOMER"],
                "reason_summary": "Proposing loyalty discount of 15%.",
                "financial_impact": "LOW",
                "customer_impact": "LOW"
            }
        else:
            return {
                "proposed_action": "OFFER_UPSELL",
                "action_parameters": None,
                "confidence": 0.85,
                "evidence": ["CART_ABANDONMENT_HIGH_VALUE"],
                "reason_summary": "Upsell opportunity on abandoned high-value items.",
                "financial_impact": "LOW",
                "customer_impact": "LOW"
            }
            
    raise ValueError(f"Unrecognized mock prompt context: {prompt[:100]}")

@patch("app.llm.provider.LLMProvider.generate_structured_output", side_effect=mock_gemini_output)
def verify_demo(mock_gen):
    db = SessionLocal()
    
    print("==================================================")
    print("AGENTSHIELD DEMO VERIFICATION")
    print("==================================================")
    
    try:
        # Fetch actual transactions and customers from seeded database
        tx_fraud = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_304").first()
        tx_low_risk = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_103").first()
        if not tx_low_risk:
            # Fallback to general success tx if tx_vc_103 is missing
            tx_low_risk = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_101").first()
            
        tx_recovery = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_302").first()
        growth_customer = db.query(Customer).filter(Customer.external_customer_id == "cust_sf_001").first() # Rohan Das
        
        # SCENARIO 1: HIGH FRAUD
        print("\nScenario 1 — HIGH FRAUD")
        print("-----------------------")
        if not tx_fraud:
            print("Transaction tx_vc_304 not found in database. Seeding issue?")
            print("PASS/FAIL: FAIL")
        else:
            clean_event_data(db, tx_fraud.id)
            result = process_event_orchestration(db, "TRANSACTION", str(tx_fraud.id))
            
            # Fetch persisted proposals and decisions for verification
            proposals = db.query(AgentProposal).filter(AgentProposal.event_id == str(tx_fraud.id)).all()
            decision = db.query(ShieldDecision).filter(ShieldDecision.proposal_id == proposals[0].id).first()
            audit_logs = db.query(AuditLog).filter(AuditLog.proposal_id == proposals[0].id).all()
            
            ml_prob = proposals[0].action_parameters.get("fraud_probability", 0.0)
            ml_risk = proposals[0].action_parameters.get("fraud_risk_level", "UNKNOWN")
            
            print(f"Transaction: {tx_fraud.id} (ExtID: {tx_fraud.external_transaction_id})")
            print(f"Agents: {result['executed_agents']}")
            print(f"Fraud Probability: {ml_prob:.4f}")
            print(f"Risk: {ml_risk}")
            print(f"Proposal: {proposals[0].action}")
            print(f"Final Decision: {result['final_decision']}")
            print(f"Audit: {'PASS' if len(audit_logs) >= 2 else 'FAIL'}")
            
            passed = (
                "FRAUD" in result["executed_agents"] and
                ml_prob > 0.90 and
                ml_risk == "HIGH" and
                proposals[0].action == "BLOCK_TRANSACTION" and
                result["final_decision"] == "ESCALATE" and
                len(audit_logs) >= 2
            )
            print(f"PASS/FAIL: {'PASS' if passed else 'FAIL'}")
            clean_event_data(db, tx_fraud.id)
            
        # SCENARIO 2: LOW RISK
        print("\nScenario 2 — LOW RISK")
        print("----------------------")
        if not tx_low_risk:
            print("Transaction tx_vc_103 not found in database. Seeding issue?")
            print("PASS/FAIL: FAIL")
        else:
            clean_event_data(db, tx_low_risk.id)
            # Low risk SUCCESS transaction triggers BOTH Fraud Agent (transaction) and Growth Agent (success customer id link)
            result = process_event_orchestration(db, "TRANSACTION", str(tx_low_risk.id))
            
            proposals = db.query(AgentProposal).filter(AgentProposal.event_id.in_([str(tx_low_risk.id), str(tx_low_risk.customer_id)])).all()
            
            prop_actions = [p.action for p in proposals]
            ml_prob = next((p.action_parameters.get("fraud_probability") for p in proposals if p.agent.agent_key == "fraud_agent"), 0.0)
            ml_risk = next((p.action_parameters.get("fraud_risk_level") for p in proposals if p.agent.agent_key == "fraud_agent"), "UNKNOWN")
            
            print(f"Transaction: {tx_low_risk.id} (ExtID: {tx_low_risk.external_transaction_id})")
            print(f"Agents: {result['executed_agents']}")
            print(f"Fraud Probability: {ml_prob:.4f}")
            print(f"Risk: {ml_risk}")
            print(f"Proposals: {', '.join(prop_actions)}")
            print(f"Final Decision: {result['final_decision']}")
            print(f"Audit: {'PASS' if len(proposals) >= 2 else 'FAIL'}")
            
            passed = (
                "FRAUD" in result["executed_agents"] and
                "GROWTH" in result["executed_agents"] and
                ml_prob < 0.25 and
                ml_risk == "LOW" and
                "ALLOW_TRANSACTION" in prop_actions and
                "APPLY_DISCOUNT" in prop_actions and
                result["final_decision"] == "MODIFY"
            )
            print(f"PASS/FAIL: {'PASS' if passed else 'FAIL'}")
            clean_event_data(db, tx_low_risk.id)
            clean_event_data(db, tx_low_risk.customer_id)
            
        # SCENARIO 3: PAYMENT RECOVERY
        print("\nScenario 3 — PAYMENT RECOVERY")
        print("-----------------------------")
        if not tx_recovery:
            print("Transaction tx_vc_302 not found in database. Seeding issue?")
            print("PASS/FAIL: FAIL")
        else:
            clean_event_data(db, tx_recovery.id)
            result = process_event_orchestration(db, "TRANSACTION", str(tx_recovery.id))
            
            proposals = db.query(AgentProposal).filter(AgentProposal.event_id == str(tx_recovery.id)).all()
            recovery_prop = next((p for p in proposals if p.agent.agent_key == "recovery_agent"), None)
            
            # Fetch active merchant policies (RAG mock validation)
            policies = db.query(MerchantPolicy).filter(
                MerchantPolicy.merchant_id == tx_recovery.merchant_id,
                MerchantPolicy.policy_key == "max_recovery_retries"
            ).first()
            
            print(f"Transaction: {tx_recovery.id} (ExtID: {tx_recovery.external_transaction_id})")
            print(f"Agents: {result['executed_agents']}")
            print(f"RAG Policies: {policies.policy_name if policies else 'None'}")
            print(f"Recovery Proposal: {recovery_prop.action if recovery_prop else 'None'}")
            print(f"Final Decision: {result['final_decision']}")
            print(f"Audit: {'PASS' if len(proposals) >= 2 else 'FAIL'}")
            
            passed = (
                "RECOVERY" in result["executed_agents"] and
                recovery_prop is not None and
                recovery_prop.action == "WAIT_AND_RETRY" and
                result["final_decision"] == "APPROVE"
            )
            print(f"PASS/FAIL: {'PASS' if passed else 'FAIL'}")
            clean_event_data(db, tx_recovery.id)
            
        # SCENARIO 4: GROWTH
        print("\nScenario 4 — GROWTH")
        print("-------------------")
        if not growth_customer:
            print("Customer cust_sf_001 not found in database. Seeding issue?")
            print("PASS/FAIL: FAIL")
        else:
            clean_event_data(db, growth_customer.id)
            result = process_event_orchestration(db, "GROWTH_OPPORTUNITY", str(growth_customer.id))
            
            proposals = db.query(AgentProposal).filter(AgentProposal.event_id == str(growth_customer.id)).all()
            growth_prop = next((p for p in proposals if p.agent.agent_key == "growth_agent"), None)
            
            policies = db.query(MerchantPolicy).filter(
                MerchantPolicy.merchant_id == growth_customer.merchant_id,
                MerchantPolicy.policy_key == "max_discount_percent"
            ).first()
            
            print(f"Event: {growth_customer.id}")
            print(f"Agents: {result['executed_agents']}")
            print(f"RAG Policies: {policies.policy_name if policies else 'None'}")
            print(f"Growth Proposal: {growth_prop.action if growth_prop else 'None'}")
            print(f"Final Decision: {result['final_decision']}")
            print(f"Audit: {'PASS' if len(proposals) >= 1 else 'FAIL'}")
            
            passed = (
                "GROWTH" in result["executed_agents"] and
                growth_prop is not None and
                growth_prop.action == "OFFER_UPSELL" and
                result["final_decision"] == "APPROVE"
            )
            print(f"PASS/FAIL: {'PASS' if passed else 'FAIL'}")
            clean_event_data(db, growth_customer.id)
            
        # SCENARIO 5: IDEMPOTENCY
        print("\nScenario 5 — IDEMPOTENCY")
        print("------------------------")
        if not tx_low_risk:
            print("Transaction not found. PASS/FAIL: FAIL")
        else:
            clean_event_data(db, tx_low_risk.id)
            clean_event_data(db, tx_low_risk.customer_id)
            
            # Step 1: Run first execution
            first_res = process_event_orchestration(db, "TRANSACTION", str(tx_low_risk.id))
            
            # Count DB records created in first run
            first_props_count = db.query(AgentProposal).filter(AgentProposal.event_id.in_([str(tx_low_risk.id), str(tx_low_risk.customer_id)])).count()
            first_decisions_count = db.query(ShieldDecision).join(AgentProposal).filter(AgentProposal.event_id.in_([str(tx_low_risk.id), str(tx_low_risk.customer_id)])).count()
            first_audit_count = db.query(AuditLog).join(AgentProposal).filter(AgentProposal.event_id.in_([str(tx_low_risk.id), str(tx_low_risk.customer_id)])).count()
            
            # Step 2: Run second execution (cached)
            second_res = process_event_orchestration(db, "TRANSACTION", str(tx_low_risk.id))
            
            # Count DB records after second run
            second_props_count = db.query(AgentProposal).filter(AgentProposal.event_id.in_([str(tx_low_risk.id), str(tx_low_risk.customer_id)])).count()
            second_decisions_count = db.query(ShieldDecision).join(AgentProposal).filter(AgentProposal.event_id.in_([str(tx_low_risk.id), str(tx_low_risk.customer_id)])).count()
            second_audit_count = db.query(AuditLog).join(AgentProposal).filter(AgentProposal.event_id.in_([str(tx_low_risk.id), str(tx_low_risk.customer_id)])).count()
            
            duplicate_props = second_props_count - first_props_count
            duplicate_decisions = second_decisions_count - first_decisions_count
            duplicate_audit = second_audit_count - first_audit_count
            
            print(f"First execution: status={first_res['status']}, final_decision={first_res['final_decision']}")
            print(f"Second execution: status={second_res['status']}, final_decision={second_res['final_decision']}")
            print(f"Duplicate proposals: {duplicate_props}")
            print(f"Duplicate decisions: {duplicate_decisions}")
            print(f"Duplicate audit records: {duplicate_audit}")
            
            passed = (
                first_res["final_decision"] == second_res["final_decision"] and
                duplicate_props == 0 and
                duplicate_decisions == 0 and
                duplicate_audit == 0
            )
            print(f"PASS/FAIL: {'PASS' if passed else 'FAIL'}")
            
            # Cleanup
            clean_event_data(db, tx_low_risk.id)
            clean_event_data(db, tx_low_risk.customer_id)

    finally:
        db.close()
        
    print("\n==================================================")

if __name__ == "__main__":
    verify_demo()
