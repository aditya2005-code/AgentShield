from abc import ABC, abstractmethod
from app.agentshield.context import EvaluationContext
from app.agentshield.schemas import CheckResultSchema

class BaseShieldCheck(ABC):
    @property
    @abstractmethod
    def check_name(self) -> str:
        pass

    @abstractmethod
    def run(self, context: EvaluationContext) -> CheckResultSchema:
        """
        Execute check rules on pre-loaded context and return a structured CheckResultSchema.
        """
        pass
