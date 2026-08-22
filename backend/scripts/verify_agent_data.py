import sys
import os

# Ensure the backend directory is in the path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database.session import SessionLocal
from app.database.models import (
    Agent, AgentPermission, MerchantPolicy, 
    AgentProposal, ShieldDecision, AuditLog
)
from app.database.models.enums import ShieldDecisionType

def verify_agent_data():
    db = SessionLocal()
    try:
        print("Starting agent database verification...")

        # 1. Verify Agents count
        agents_count = db.query(Agent).count()
        print(f"- Core Agents: {agents_count} (Expected: 3)")
        assert agents_count == 3, f"Unexpected agent count: {agents_count}"

        # 2. Verify Agent permissions exist
        perms_count = db.query(AgentPermission).count()
        print(f"- Agent Permissions: {perms_count} (Expected: >= 6)")
        assert perms_count >= 6, f"Unexpected permission count: {perms_count}"

        # 3. Verify Merchant policies exist
        policies_count = db.query(MerchantPolicy).count()
        print(f"- Merchant Policies: {policies_count} (Expected: >= 4)")
        assert policies_count >= 4, f"Unexpected policy count: {policies_count}"

        # 4. Verify Proposals count
        proposals_count = db.query(AgentProposal).count()
        print(f"- Agent Proposals: {proposals_count} (Expected: >= 3)")
        assert proposals_count >= 3, f"Unexpected proposals count: {proposals_count}"

        # 5. Verify Shield Decisions count and types
        decisions_count = db.query(ShieldDecision).count()
        print(f"- Shield Decisions: {decisions_count} (Expected: >= 3)")
        assert decisions_count >= 3, f"Unexpected decisions count: {decisions_count}"

        decisions = db.query(ShieldDecision).all()
        has_approve = any(d.decision == ShieldDecisionType.APPROVE for d in decisions)
        has_modify = any(d.decision == ShieldDecisionType.MODIFY for d in decisions)
        
        print(f"  - Has APPROVE decision: {has_approve} (Expected: True)")
        print(f"  - Has MODIFY decision: {has_modify} (Expected: True)")
        
        assert has_approve, "Missing APPROVE decision in database"
        assert has_modify, "Missing MODIFY decision in database"

        # 6. Verify proposal connections
        print("\nVerifying agent proposals mapping...")
        for p in db.query(AgentProposal).all():
            assert p.agent is not None, f"Proposal {p.id} has no agent connection"
            print(f"- Proposal '{p.action}' correctly links to Agent '{p.agent.name}' (Verified).")

        # 7. Verify Shield decision connections
        print("\nVerifying shield decisions mapping...")
        for d in db.query(ShieldDecision).all():
            assert d.proposal is not None, f"Shield decision {d.id} has no proposal connection"
            print(f"- Decision '{d.decision}' correctly links to Proposal '{d.proposal.action}' (Verified).")

        # 8. Verify Audit Logs exist
        audit_count = db.query(AuditLog).count()
        print(f"\n- Audit Logs: {audit_count} (Expected: >= 6)")
        assert audit_count >= 6, f"Unexpected audit logs count: {audit_count}"

        # 9. Verify Lifecycle linkages
        print("\nVerifying lifecycle traces...")
        proposals = db.query(AgentProposal).all()
        for p in proposals:
            # Lifecycle: Agent -> Proposal -> Shield Decision -> Audit Log
            agent = p.agent
            decision = p.shield_decision
            audit_logs = p.audit_logs
            
            assert agent is not None, "Lifecycle break: Proposal has no Agent"
            assert decision is not None, "Lifecycle break: Proposal has no Shield Decision"
            assert len(audit_logs) >= 2, f"Lifecycle break: Proposal {p.id} has fewer than 2 audit logs (creation + decision)"
            
            print(f"- Trace OK for Event ID '{p.event_id}': Agent '{agent.agent_key}' -> Proposal ID '{p.id}' -> Decision ID '{decision.id}' -> {len(audit_logs)} logs (Verified).")

        print("\n[OK] Agent Database Verification: PASSED")
    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    verify_agent_data()
