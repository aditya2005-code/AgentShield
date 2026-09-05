import { API_URL } from '../config';
import { 
  Agent, Merchant, MerchantPolicy, Transaction, TransactionDetail,
  ActionProposal, ProposalDetail, ShieldDecision, ShieldDecisionDetail,
  AuditLog, DemoScenario
} from '../../types/api';

// Custom API Error class to handle non-2xx responses
export class ApiError extends Error {
  status: number;
  info: any;

  constructor(message: string, status: number, info: any = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.info = info;
  }
}

// Generic Fetch Helper
async function fetchApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_URL}${path.startsWith('/') ? '' : '/'}${path}`;
  
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorInfo = null;
    try {
      errorInfo = await response.json();
    } catch {
      // Ignore parsing errors for non-JSON response bodies
    }
    throw new ApiError(
      errorInfo?.detail || `API request failed with status ${response.status}`,
      response.status,
      errorInfo
    );
  }

  return response.json() as Promise<T>;
}

// Helper to construct query strings from parameter dicts
function buildQueryString(params: Record<string, any> = {}): string {
  const cleanParams: Record<string, string> = {};
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      cleanParams[key] = String(val);
    }
  });
  const searchParams = new URLSearchParams(cleanParams);
  const qString = searchParams.toString();
  return qString ? `?${qString}` : '';
}

// API v1 Client Endpoints

// 1. Health Status check
export async function getHealthStatus(): Promise<{ status: string; database: string; day?: number }> {
  return fetchApi<{ status: string; database: string; day?: number }>('/health', { cache: 'no-store' });
}

// 2. Agents APIs
export async function getAgents(): Promise<Agent[]> {
  return fetchApi<Agent[]>('/api/v1/agents');
}

export async function getAgentById(agentId: string): Promise<Agent> {
  return fetchApi<Agent>(`/api/v1/agents/${agentId}`);
}

// 3. Merchants APIs
export async function getMerchants(): Promise<Merchant[]> {
  return fetchApi<Merchant[]>('/api/v1/merchants');
}

export async function getMerchantById(merchantId: string): Promise<Merchant> {
  return fetchApi<Merchant>(`/api/v1/merchants/${merchantId}`);
}

export async function getMerchantPolicies(merchantId: string): Promise<MerchantPolicy[]> {
  return fetchApi<MerchantPolicy[]>(`/api/v1/merchants/${merchantId}/policies`);
}

// 4. Transactions APIs
export async function getTransactions(params?: {
  limit?: number;
  offset?: number;
  merchant_id?: string;
  customer_id?: string;
  status?: string;
}): Promise<Transaction[]> {
  const qString = buildQueryString(params);
  return fetchApi<Transaction[]>(`/api/v1/transactions${qString}`);
}

export async function getTransactionById(transactionId: string): Promise<TransactionDetail> {
  return fetchApi<TransactionDetail>(`/api/v1/transactions/${transactionId}`);
}

// 5. Proposals APIs
export async function getProposals(params?: {
  limit?: number;
  offset?: number;
  agent_id?: string;
  merchant_id?: string;
  status?: string;
  event_type?: string;
}): Promise<ActionProposal[]> {
  const qString = buildQueryString(params);
  return fetchApi<ActionProposal[]>(`/api/v1/proposals${qString}`);
}

export async function getProposalById(proposalId: string): Promise<ProposalDetail> {
  return fetchApi<ProposalDetail>(`/api/v1/proposals/${proposalId}`);
}

// 6. Shield Decisions APIs
export async function getDecisions(params?: {
  limit?: number;
  offset?: number;
  decision?: string;
  requires_human_review?: boolean;
}): Promise<ShieldDecision[]> {
  const qString = buildQueryString(params);
  return fetchApi<ShieldDecision[]>(`/api/v1/decisions${qString}`);
}

export async function getDecisionById(decisionId: string): Promise<ShieldDecisionDetail> {
  return fetchApi<ShieldDecisionDetail>(`/api/v1/decisions/${decisionId}`);
}

// 7. Audit Logs APIs
export async function getAuditLogs(params?: {
  limit?: number;
  offset?: number;
  merchant_id?: string;
  agent_id?: string;
  proposal_id?: string;
  decision_id?: string;
  event_type?: string;
}): Promise<AuditLog[]> {
  const qString = buildQueryString(params);
  return fetchApi<AuditLog[]>(`/api/v1/audit-logs${qString}`);
}

// 8. Demo Scenario APIs
export async function getDemoScenarios(): Promise<{ scenarios: string[] }> {
  return fetchApi<{ scenarios: string[] }>('/api/v1/demo/scenarios');
}

export async function getDemoScenario(scenarioType: string): Promise<DemoScenario> {
  return fetchApi<DemoScenario>(`/api/v1/demo/scenarios/${scenarioType}`);
}

// 9. Interactive Event Processing API
export interface ProcessEventPayload {
  event_type: string;
  event_id: string;
}

export interface ProcessEventResponse {
  event_id: string;
  status: string;
  executed_agents: string[];
  proposals: Array<{
    proposal_id: string;
    agent_key: string;
    action: string;
    status: string;
  }>;
  final_decision: string | null;
  decision_id: string | null;
  decision_details: Array<{
    decision_id: string;
    decision: string;
    final_action: string;
    reason: string;
  }>;
}

export async function processEvent(payload: ProcessEventPayload): Promise<ProcessEventResponse> {
  return fetchApi<ProcessEventResponse>('/api/v1/agentshield/process-event', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

