from enum import Enum

class MerchantStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class RiskProfile(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"

class AgentType(str, Enum):
    FRAUD = "FRAUD"
    RECOVERY = "RECOVERY"
    GROWTH = "GROWTH"

class AgentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class ProposalStatus(str, Enum):
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"

class ImpactLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ShieldDecisionType(str, Enum):
    APPROVE = "APPROVE"
    MODIFY = "MODIFY"
    ESCALATE = "ESCALATE"
    REJECT = "REJECT"

class ShieldCheckStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"

class AuditEventType(str, Enum):
    AGENT_PROPOSAL_CREATED = "AGENT_PROPOSAL_CREATED"
    SHIELD_DECISION_CREATED = "SHIELD_DECISION_CREATED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
