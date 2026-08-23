from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from app.database.models.agent_proposal import AgentProposal

class BaseAgent(ABC):
    @property
    @abstractmethod
    def agent_key(self) -> str:
        """
        Return the unique identifier string for the agent (e.g. 'fraud_agent').
        """
        pass

    @abstractmethod
    def execute(
        self,
        event_type: str,
        event_id: str,
        merchant_id: str,
        db: Session
    ) -> AgentProposal:
        """
        Gather agent-specific context and perform deterministic heuristic rules analysis.
        Return an unsaved AgentProposal database model instance.
        """
        pass
