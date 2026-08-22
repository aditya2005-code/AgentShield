import sys
import os
from datetime import datetime, timezone
from decimal import Decimal

# Ensure the backend directory is in the path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database.session import SessionLocal
from app.database.models import (
    Agent, AgentPermission, Merchant, MerchantPolicy, 
    AgentProposal, ShieldDecision, AuditLog, Transaction
)
from app.database.models.enums import (
    AgentType, AgentStatus, ProposalStatus, ImpactLevel, 
    ShieldDecisionType, AuditEventType
)

def seed_agent_data():
    db = SessionLocal()
    try:
        print("Starting agent data seeding...")

        # 1. Seed Agents
        agents_data = [
            {"key": "fraud_agent", "type": AgentType.FRAUD, "name": "Fraud Detection Agent", "desc": "Analyzes transaction risk using ML and LLM investigation"},
            {"key": "recovery_agent", "type": AgentType.RECOVERY, "name": "Payment Recovery Agent", "desc": "Handles dunning sequences and payment retry strategies"},
            {"key": "growth_agent", "type": AgentType.GROWTH, "name": "Growth Incentives Agent", "desc": "Decides risk-adjusted promotions and limits for customers"},
        ]

        agents = {}
        for a_info in agents_data:
            existing = db.query(Agent).filter(Agent.agent_key == a_info["key"]).first()
            if not existing:
                agent = Agent(
                    agent_key=a_info["key"],
                    agent_type=a_info["type"],
                    name=a_info["name"],
                    description=a_info["desc"],
                    status=AgentStatus.ACTIVE
                )
                db.add(agent)
                db.flush()
                agents[agent.agent_key] = agent
                print(f"Created agent: {agent.name}")
            else:
                agents[existing.agent_key] = existing
                print(f"Agent already exists: {existing.name}")

        # 2. Seed Agent Permissions
        permissions_data = [
            # Fraud Agent
            {"agent_key": "fraud_agent", "action": "STEP_UP_VERIFICATION", "allowed": True, "review": False},
            {"agent_key": "fraud_agent", "action": "BLOCK_TRANSACTION", "allowed": True, "review": True},
            
            # Recovery Agent
            {"agent_key": "recovery_agent", "action": "WAIT_AND_RETRY", "allowed": True, "review": False},
            {"agent_key": "recovery_agent", "action": "REQUEST_NEW_PAYMENT_METHOD", "allowed": True, "review": False},
            
            # Growth Agent
            {"agent_key": "growth_agent", "action": "APPLY_DISCOUNT", "allowed": True, "review": False},
            {"agent_key": "growth_agent", "action": "SEND_PROMOTION", "allowed": True, "review": False},
        ]

        for p_info in permissions_data:
            ag = agents[p_info["agent_key"]]
            existing = db.query(AgentPermission).filter(
                AgentPermission.agent_id == ag.id,
                AgentPermission.action == p_info["action"]
            ).first()
            if not existing:
                perm = AgentPermission(
                    agent_id=ag.id,
                    action=p_info["action"],
                    is_allowed=p_info["allowed"],
                    requires_human_review=p_info["review"]
                )
                db.add(perm)
                print(f"Created permission: {perm.action} for {ag.name}")
            else:
                print(f"Permission already exists: {existing.action} for {ag.name}")

        # 3. Seed Merchant Policies (for VeloCart Electronics - velocart-electronics)
        merchant = db.query(Merchant).filter(Merchant.slug == "velocart-electronics").first()
        if not merchant:
            print("Error: VeloCart Electronics merchant not found. Please run core seed script first.")
            return

        policies_data = [
            {"key": "max_discount_percent", "name": "Maximum Discount Percentage Allowed", "val": {"value": 10}},
            {"key": "max_recovery_retries", "name": "Maximum Payment Recovery Retries", "val": {"value": 3}},
            {"key": "high_value_threshold", "name": "High Value Transaction Threshold", "val": {"value": 50000}},
            {"key": "auto_block_threshold", "name": "Auto Block Risk Score Threshold", "val": {"value": 0.90}},
        ]

        for po_info in policies_data:
            existing = db.query(MerchantPolicy).filter(
                MerchantPolicy.merchant_id == merchant.id,
                MerchantPolicy.policy_key == po_info["key"]
            ).first()
            if not existing:
                policy = MerchantPolicy(
                    merchant_id=merchant.id,
                    policy_key=po_info["key"],
                    policy_name=po_info["name"],
                    policy_value=po_info["val"],
                    is_active=True
                )
                db.add(policy)
                print(f"Created merchant policy: {policy.policy_key}")
            else:
                print(f"Merchant policy already exists: {existing.policy_key}")

        # 4. Seed Proposals, Decisions, and Audit Logs
        # Scenario 1 - FRAUD
        # Use transaction tx_vc_304 (suspicious pending transaction for Kabir Singh)
        tx_fraud = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_304").first()
        if tx_fraud:
            # Check if proposal already exists
            existing_prop = db.query(AgentProposal).filter(
                AgentProposal.event_type == "TRANSACTION",
                AgentProposal.event_id == str(tx_fraud.id)
            ).first()
            if not existing_prop:
                # Create Proposal
                prop = AgentProposal(
                    agent_id=agents["fraud_agent"].id,
                    merchant_id=merchant.id,
                    event_type="TRANSACTION",
                    event_id=str(tx_fraud.id),
                    action="STEP_UP_VERIFICATION",
                    action_parameters=None,
                    confidence=Decimal("0.8800"),
                    financial_impact=ImpactLevel.MEDIUM,
                    customer_impact=ImpactLevel.MEDIUM,
                    evidence=["NEW_DEVICE", "UNUSUAL_LOCATION", "HIGH_TRANSACTION_VELOCITY"],
                    reason_summary="Kabir Singh transaction occurred at anomalous location (Moscow) using untrusted device.",
                    status=ProposalStatus.REVIEWED
                )
                db.add(prop)
                db.flush()

                # Create Audit Log for Proposal Creation
                audit_prop = AuditLog(
                    merchant_id=merchant.id,
                    agent_id=agents["fraud_agent"].id,
                    proposal_id=prop.id,
                    event_type=AuditEventType.AGENT_PROPOSAL_CREATED,
                    action="AGENT_PROPOSAL_CREATED",
                    details={"action": prop.action, "confidence": float(prop.confidence), "evidence": prop.evidence}
                )
                db.add(audit_prop)

                # Create Shield Decision
                dec = ShieldDecision(
                    proposal_id=prop.id,
                    decision=ShieldDecisionType.APPROVE,
                    final_action="STEP_UP_VERIFICATION",
                    final_action_parameters=None,
                    checks=[{
                        "name": "AGENT_AUTHORIZATION",
                        "status": "PASSED",
                        "message": "Fraud Agent is allowed to propose step-up verification."
                    }],
                    reason="Approved. Step-up verification is appropriate for medium-high risk anomaly.",
                    requires_human_review=False
                )
                db.add(dec)
                db.flush()

                # Create Audit Log for Decision Creation
                audit_dec = AuditLog(
                    merchant_id=merchant.id,
                    agent_id=agents["fraud_agent"].id,
                    proposal_id=prop.id,
                    decision_id=dec.id,
                    event_type=AuditEventType.SHIELD_DECISION_CREATED,
                    action="SHIELD_DECISION_CREATED",
                    details={"decision": dec.decision, "final_action": dec.final_action}
                )
                db.add(audit_dec)
                print("Seeded Scenario 1 (Fraud): STEP_UP_VERIFICATION approved.")
            else:
                print("Scenario 1 (Fraud) proposal already exists.")

        # Scenario 2 - RECOVERY
        # Use transaction tx_vc_302 (failed transaction for Kabir Singh)
        tx_failed = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_302").first()
        if tx_failed:
            existing_prop = db.query(AgentProposal).filter(
                AgentProposal.event_type == "PAYMENT_FAILURE",
                AgentProposal.event_id == str(tx_failed.id)
            ).first()
            if not existing_prop:
                prop = AgentProposal(
                    agent_id=agents["recovery_agent"].id,
                    merchant_id=merchant.id,
                    event_type="PAYMENT_FAILURE",
                    event_id=str(tx_failed.id),
                    action="WAIT_AND_RETRY",
                    action_parameters={"wait_hours": 24},
                    confidence=Decimal("0.8200"),
                    financial_impact=ImpactLevel.LOW,
                    customer_impact=ImpactLevel.LOW,
                    evidence=["CARD_DECLINED_INSUFFICIENT_FUNDS"],
                    reason_summary="Credit Card declined for insufficient funds. Proposing temporary wait and retry sequence.",
                    status=ProposalStatus.REVIEWED
                )
                db.add(prop)
                db.flush()

                audit_prop = AuditLog(
                    merchant_id=merchant.id,
                    agent_id=agents["recovery_agent"].id,
                    proposal_id=prop.id,
                    event_type=AuditEventType.AGENT_PROPOSAL_CREATED,
                    action="AGENT_PROPOSAL_CREATED",
                    details={"action": prop.action, "confidence": float(prop.confidence), "evidence": prop.evidence}
                )
                db.add(audit_prop)

                dec = ShieldDecision(
                    proposal_id=prop.id,
                    decision=ShieldDecisionType.APPROVE,
                    final_action="WAIT_AND_RETRY",
                    final_action_parameters={"wait_hours": 24},
                    checks=[{
                        "name": "DUNNING_RETRY_LIMIT",
                        "status": "PASSED",
                        "message": "Retry count (0) is below merchant max retry policy (3)."
                    }],
                    reason="Approved. Standard dunning wait-and-retry sequence.",
                    requires_human_review=False
                )
                db.add(dec)
                db.flush()

                audit_dec = AuditLog(
                    merchant_id=merchant.id,
                    agent_id=agents["recovery_agent"].id,
                    proposal_id=prop.id,
                    decision_id=dec.id,
                    event_type=AuditEventType.SHIELD_DECISION_CREATED,
                    action="SHIELD_DECISION_CREATED",
                    details={"decision": dec.decision, "final_action": dec.final_action}
                )
                db.add(audit_dec)
                print("Seeded Scenario 2 (Recovery): WAIT_AND_RETRY approved.")
            else:
                print("Scenario 2 (Recovery) proposal already exists.")

        # Scenario 3 - GROWTH
        # Event type growth_opportunity for a merchant
        event_growth_id = "growth_opp_sf_999"
        existing_prop = db.query(AgentProposal).filter(
            AgentProposal.event_type == "GROWTH_OPPORTUNITY",
            AgentProposal.event_id == event_growth_id
        ).first()
        if not existing_prop:
            # We seed a proposal where growth agent wants to apply a 25% discount, 
            # but the policy max discount is 10%, so Shield MODIFY it to 10%
            prop = AgentProposal(
                agent_id=agents["growth_agent"].id,
                merchant_id=merchant.id,
                event_type="GROWTH_OPPORTUNITY",
                event_id=event_growth_id,
                action="APPLY_DISCOUNT",
                action_parameters={"discount_percent": 25},
                confidence=Decimal("0.8500"),
                financial_impact=ImpactLevel.MEDIUM,
                customer_impact=ImpactLevel.LOW,
                evidence=["CART_ABANDONMENT_HIGH_VALUE"],
                reason_summary="High-value cart abandoned by customer. Proposing 25% recovery discount promotion.",
                status=ProposalStatus.REVIEWED
            )
            db.add(prop)
            db.flush()

            audit_prop = AuditLog(
                merchant_id=merchant.id,
                agent_id=agents["growth_agent"].id,
                proposal_id=prop.id,
                event_type=AuditEventType.AGENT_PROPOSAL_CREATED,
                action="AGENT_PROPOSAL_CREATED",
                details={"action": prop.action, "confidence": float(prop.confidence), "evidence": prop.evidence}
            )
            db.add(audit_prop)

            dec = ShieldDecision(
                proposal_id=prop.id,
                decision=ShieldDecisionType.MODIFY,
                final_action="APPLY_DISCOUNT",
                final_action_parameters={"discount_percent": 10},
                modified_from={"discount_percent": 25},
                checks=[{
                    "name": "MAX_DISCOUNT_CHECK",
                    "status": "FAILED",
                    "message": "Proposed discount of 25% exceeds the merchant maximum discount policy (10%)."
                }],
                reason="Modified. The requested discount exceeds the merchant maximum discount policy. Adjusted to policy limit of 10%.",
                requires_human_review=False
            )
            db.add(dec)
            db.flush()

            audit_dec = AuditLog(
                merchant_id=merchant.id,
                agent_id=agents["growth_agent"].id,
                proposal_id=prop.id,
                decision_id=dec.id,
                event_type=AuditEventType.SHIELD_DECISION_CREATED,
                action="SHIELD_DECISION_CREATED",
                details={"decision": dec.decision, "final_action": dec.final_action, "modified_from": dec.modified_from}
            )
            db.add(audit_dec)
            print("Seeded Scenario 3 (Growth): APPLY_DISCOUNT modified from 25% to 10%.")
        else:
            print("Scenario 3 (Growth) proposal already exists.")

        db.commit()
        print("Agent database seeding complete successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_agent_data()
