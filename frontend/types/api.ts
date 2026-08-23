// Central TypeScript type definitions matching backend API schemas

export type AgentType = 'FRAUD' | 'RECOVERY' | 'GROWTH';
export type AgentStatus = 'ACTIVE' | 'INACTIVE';

export interface Agent {
  id: string;
  agent_key: string;
  agent_type: AgentType;
  name: string;
  description: string | null;
  status: AgentStatus;
  created_at: string;
  updated_at: string;
}

export interface AgentSummary {
  id: string;
  agent_key: string;
  agent_type: AgentType;
  name: string;
}

export type MerchantStatus = 'ACTIVE' | 'INACTIVE';

export interface Merchant {
  id: string;
  name: string;
  slug: string;
  status: MerchantStatus;
  created_at: string;
  updated_at: string;
}

export interface MerchantSummary {
  id: string;
  name: string;
  slug: string;
}

export interface CustomerSummary {
  id: string;
  external_customer_id: string;
  email: string;
  full_name: string;
}

export interface DeviceSummary {
  id: string;
  device_fingerprint: string;
  device_type: string;
}

export type TransactionStatus = 'PENDING' | 'SUCCESS' | 'FAILED' | 'BLOCKED';

export interface Transaction {
  id: string;
  external_transaction_id: string;
  merchant_id: string;
  customer_id: string;
  device_id: string | null;
  amount: number;
  currency: string;
  payment_method: string;
  location: string;
  status: TransactionStatus;
  occurred_at: string;
  created_at: string;
}

export interface TransactionDetail extends Transaction {
  merchant: MerchantSummary;
  customer: CustomerSummary;
  device: DeviceSummary | null;
}

export type ImpactLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type ProposalStatus = 'PENDING' | 'REVIEWED' | 'EXECUTED' | 'REJECTED';

export interface ActionProposal {
  proposal_id: string;
  agent_id: string;
  merchant_id: string;
  event_type: string;
  event_id: string;
  action: string;
  action_parameters: Record<string, any> | null;
  confidence: number;
  financial_impact: ImpactLevel;
  customer_impact: ImpactLevel;
  evidence: any;
  reason_summary: string;
  status: ProposalStatus;
  created_at: string;
}

export interface ProposalDetail {
  proposal: ActionProposal;
  agent: AgentSummary;
  merchant: MerchantSummary;
  shield_decision: ShieldDecision | null;
}

export type ShieldDecisionType = 'APPROVE' | 'MODIFY' | 'ESCALATE' | 'REJECT';

export interface ShieldDecision {
  decision_id: string;
  proposal_id: string;
  decision: ShieldDecisionType;
  final_action: string;
  final_action_parameters: Record<string, any> | null;
  modified_from: Record<string, any> | null;
  checks: Array<Record<string, any>>;
  reason: string;
  requires_human_review: boolean;
  created_at: string;
}

export interface ProposalSummary {
  proposal_id: string;
  event_type: string;
  event_id: string;
  action: string;
  confidence: number;
  status: string;
}

export interface ShieldDecisionDetail extends ShieldDecision {
  proposal: ProposalSummary;
  agent: AgentSummary | null;
}

export interface MerchantPolicy {
  id: string;
  merchant_id: string;
  policy_key: string;
  policy_name: string;
  policy_value: Record<string, any>;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type AuditEventType = 'AGENT_PROPOSAL_CREATED' | 'SHIELD_DECISION_CREATED' | 'ACTION_EXECUTED';

export interface AuditLog {
  id: string;
  merchant_id: string | null;
  agent_id: string | null;
  proposal_id: string | null;
  decision_id: string | null;
  event_type: AuditEventType;
  action: string;
  details: Record<string, any>;
  created_at: string;
}

export interface DemoScenario {
  event: Record<string, any>;
  agent: Agent;
  proposal: ActionProposal;
  merchant_policies: MerchantPolicy[];
  shield_decision: ShieldDecision;
  audit_logs: AuditLog[];
}
