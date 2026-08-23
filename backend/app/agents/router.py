from sqlalchemy.orm import Session
from app.database.models.agent import Agent
from app.database.models.agent_proposal import AgentProposal
from app.database.models.enums import AgentType
from app.agents.fraud.agent import FraudAgent
from app.agents.recovery.agent import RecoveryAgent
from app.agents.growth.agent import GrowthAgent

def execute_agent(
    agent_type: AgentType,
    event_type: str,
    event_id: str,
    merchant_id: str,
    db: Session
) -> AgentProposal:
    # 1. Validate the agent registry record exists
    agent = db.query(Agent).filter(Agent.agent_type == agent_type).first()
    if not agent:
        raise ValueError(f"Agent with type '{agent_type.value}' not found in registry.")

    # 2. Validate the event compatibility rules
    normal_agent_type = agent_type.value.upper()
    normal_event_type = event_type.upper()

    if normal_agent_type == "FRAUD" and normal_event_type != "TRANSACTION":
        raise ValueError(f"Fraud Agent only supports event_type 'TRANSACTION', got '{event_type}'")
    elif normal_agent_type == "RECOVERY" and normal_event_type not in ("PAYMENT_FAILURE", "TRANSACTION"):
        raise ValueError(f"Recovery Agent only supports event_type 'PAYMENT_FAILURE' or 'TRANSACTION', got '{event_type}'")
    elif normal_agent_type == "GROWTH" and normal_event_type != "GROWTH_OPPORTUNITY":
        raise ValueError(f"Growth Agent only supports event_type 'GROWTH_OPPORTUNITY', got '{event_type}'")

    # 3. Route to the specialized instance
    if normal_agent_type == "FRAUD":
        agent_instance = FraudAgent()
    elif normal_agent_type == "RECOVERY":
        agent_instance = RecoveryAgent()
    elif normal_agent_type == "GROWTH":
        agent_instance = GrowthAgent()
    else:
        raise ValueError(f"Routing logic for agent type '{agent_type}' is not configured.")

    # 4-6. Execute context collection and analysis rules
    return agent_instance.execute(event_type, event_id, merchant_id, db)
