'use client';

import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { EmptyState } from '@/components/shared/empty-state';
import { StatusBadge } from '@/components/shared/status-badge';
import { 
  processEvent, 
  getProposalById, 
  getMerchantPolicies, 
  getAuditLogs
} from '@/lib/api/client';
import { DemoScenario, Transaction, ActionProposal, ShieldDecision, AuditLog, MerchantPolicy, Agent } from '@/types/api';
import { 
  Play, 
  Shield, 
  ArrowDown, 
  Cpu, 
  FileText, 
  CheckCircle2, 
  Activity, 
  Settings, 
  ArrowRight,
  Sparkles,
  Info,
  Clock
} from 'lucide-react';

const DEMO_SCENARIOS = [
  {
    id: 'scenario_1',
    name: 'Scenario 1: High Fraud Anomaly (tx_vc_304)',
    event_type: 'TRANSACTION',
    event_id: '180b50ae-c0ed-4a08-89ee-b103d7558c38',
    details: {
      customer: 'Kabir Singh',
      merchant: 'VeloCart Electronics',
      amount: 'INR 120,000',
      status: 'PENDING',
      location: 'Moscow, Russia',
      payment_method: 'Credit Card',
      event_type: 'TRANSACTION',
      description: 'Suspicious transaction originating from Moscow, Russia using a new device.'
    }
  },
  {
    id: 'scenario_2',
    name: 'Scenario 2: Low Risk Success (tx_vc_103)',
    event_type: 'TRANSACTION',
    event_id: '7b4003f3-0d57-4257-9ce8-fc4a58b71fb3',
    details: {
      customer: 'Aarav Sharma',
      merchant: 'VeloCart Electronics',
      amount: 'INR 12,000',
      status: 'SUCCESS',
      location: 'Mumbai, India',
      payment_method: 'UPI',
      event_type: 'TRANSACTION',
      description: 'Standard transaction in Mumbai from a trusted device.'
    }
  },
  {
    id: 'scenario_3',
    name: 'Scenario 3: Payment Failure & Recovery (tx_vc_302)',
    event_type: 'TRANSACTION',
    event_id: 'df73f35a-b4c2-48df-adff-e0e61f7c2adb',
    details: {
      customer: 'Kabir Singh',
      merchant: 'VeloCart Electronics',
      amount: 'INR 95,000',
      status: 'FAILED',
      location: 'Delhi, India',
      payment_method: 'Credit Card',
      event_type: 'TRANSACTION',
      description: 'Failed credit card transaction triggering Recovery wait-and-retry.'
    }
  },
  {
    id: 'scenario_4',
    name: 'Scenario 4: Growth Opportunity (Rohan Das)',
    event_type: 'GROWTH_OPPORTUNITY',
    event_id: '13f0ed90-562b-4449-86c3-83f407ca5326',
    details: {
      customer: 'Rohan Das',
      merchant: 'ScribeFlow Premium',
      amount: 'INR 45,000 (Cart Value)',
      status: 'CART_ABANDONED',
      location: 'Kolkata, India',
      payment_method: 'N/A',
      event_type: 'GROWTH_OPPORTUNITY',
      description: 'Cart abandonment event triggering Growth incentives limits check.'
    }
  }
];

interface ProposalExecutionItem {
  proposal: ActionProposal;
  agent: Agent;
  shield_decision: ShieldDecision;
  audit_logs: AuditLog[];
}

export default function InteractiveDemoPage() {
  const [selectedScenarioIndex, setSelectedScenarioIndex] = useState<number>(0);
  const [scenarioData, setScenarioData] = useState<DemoScenario | null>(null);
  const [proposalsList, setProposalsList] = useState<ProposalExecutionItem[]>([]);
  const [activeProposalIdx, setActiveProposalIdx] = useState<number>(0);
  const [workflowMeta, setWorkflowMeta] = useState<{
    status: string;
    final_decision: string;
    decision_id: string;
  } | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isLoadingDetails, setIsLoadingDetails] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [idempotentHit, setIdempotentHit] = useState<boolean>(false);
  const [runCount, setRunCount] = useState<Record<string, number>>({});

  const currentScenario = DEMO_SCENARIOS[selectedScenarioIndex];

  // Helper formatting for actions
  const formatActionDisplay = (action: string, params: Record<string, any> | null) => {
    if (!action) return 'None';
    const actionUpper = action.toUpperCase();
    if (actionUpper === 'APPLY_DISCOUNT' && params?.discount_percent !== undefined) {
      return `${params.discount_percent}% Discount`;
    }
    if (actionUpper === 'WAIT_AND_RETRY' && params?.wait_hours !== undefined) {
      return `Retry after ${params.wait_hours} hr(s)`;
    }
    if (actionUpper === 'STEP_UP_VERIFICATION') {
      return 'Step-up MFA Verification';
    }
    return action;
  };

  const handleSelectProposal = (idx: number) => {
    setActiveProposalIdx(idx);
    const item = proposalsList[idx];
    if (item && scenarioData) {
      setScenarioData({
        ...scenarioData,
        agent: item.agent,
        proposal: item.proposal,
        shield_decision: item.shield_decision,
        audit_logs: item.audit_logs
      });
    }
  };

  const handleProcessEvent = async () => {
    setIsProcessing(true);
    setError(null);
    setIdempotentHit(false);
    setScenarioData(null);
    setProposalsList([]);
    setActiveProposalIdx(0);
    setWorkflowMeta(null);

    const eventKey = `${currentScenario.event_type}_${currentScenario.event_id}`;
    const nextRunCount = (runCount[eventKey] || 0) + 1;
    setRunCount(prev => ({ ...prev, [eventKey]: nextRunCount }));

    try {
      // 1. POST request to backend orchestrator
      const response = await processEvent({
        event_type: currentScenario.event_type,
        event_id: currentScenario.event_id
      });

      // Track if it's cached/idempotent
      if (nextRunCount > 1) {
        setIdempotentHit(true);
      }

      if (response.status === 'FAILED') {
        throw new Error('Backend event processing orchestration failed.');
      }

      setIsLoadingDetails(true);

      // 2. Fetch full details for the resulting proposals and policy structures
      let merchantPolicies: MerchantPolicy[] = [];

      if (response.proposals && response.proposals.length > 0) {
        // Fetch proposal details for each agent
        const detailsPromises = response.proposals.map(p => getProposalById(p.proposal_id));
        const resolvedDetails = await Promise.all(detailsPromises);
        
        // Find merchant context and policies
        const merchantId = resolvedDetails[0].proposal.merchant_id;
        merchantPolicies = await getMerchantPolicies(merchantId);

        // Fetch audit logs for all proposals
        const auditPromises = response.proposals.map(p => getAuditLogs({ proposal_id: p.proposal_id }));
        const resolvedAudits = await Promise.all(auditPromises);

        // Construct items
        const items: ProposalExecutionItem[] = resolvedDetails.map((detail, idx) => ({
          proposal: detail.proposal,
          agent: {
            id: detail.agent.id,
            agent_key: detail.agent.agent_key,
            agent_type: detail.agent.agent_type,
            name: detail.agent.name,
            description: detail.agent.agent_type === 'FRAUD' 
              ? 'Analyzes transaction risk using ML inference and LLM investigation' 
              : detail.agent.agent_type === 'RECOVERY' 
              ? 'Handles dunning sequences and payment retry strategies' 
              : 'Decides risk-adjusted promotions and limits for customers',
            status: 'ACTIVE',
            created_at: '',
            updated_at: ''
          },
          shield_decision: detail.shield_decision || {
            decision_id: response.decision_id || '',
            proposal_id: detail.proposal.proposal_id,
            decision: (response.final_decision as any) || 'APPROVE',
            final_action: response.decision_details?.[idx]?.final_action || detail.proposal.action,
            final_action_parameters: detail.proposal.action_parameters,
            modified_from: null,
            checks: [],
            reason: response.decision_details?.[idx]?.reason || 'Approved automatically.',
            requires_human_review: false,
            created_at: ''
          },
          audit_logs: resolvedAudits[idx] || []
        }));

        setProposalsList(items);
        setWorkflowMeta({
          status: response.status,
          final_decision: response.final_decision || 'APPROVE',
          decision_id: response.decision_id || ''
        });

        // Determine default active proposal index based on scenario focus
        let initialIdx = 0;
        if (currentScenario.id === 'scenario_3') {
          const recIdx = items.findIndex(it => it.agent.agent_type === 'RECOVERY');
          if (recIdx !== -1) initialIdx = recIdx;
        } else if (currentScenario.id === 'scenario_4') {
          const grIdx = items.findIndex(it => it.agent.agent_type === 'GROWTH');
          if (grIdx !== -1) initialIdx = grIdx;
        }
        setActiveProposalIdx(initialIdx);

        const activeItem = items[initialIdx];
        setScenarioData({
          event: currentScenario.details,
          agent: activeItem.agent,
          proposal: activeItem.proposal,
          merchant_policies: merchantPolicies,
          shield_decision: activeItem.shield_decision,
          audit_logs: activeItem.audit_logs
        });
      } else {
        throw new Error('No agent action proposals were successfully created.');
      }

    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Error occurred during live event simulation.');
    } finally {
      setIsProcessing(false);
      setIsLoadingDetails(false);
    }
  };

  // Safe checks for rendering
  const mlSignal = scenarioData?.proposal?.action_parameters;
  const isMLPresent = mlSignal && (mlSignal.fraud_probability !== undefined || mlSignal.ml_signal_available !== undefined);

  return (
    <div className="space-y-6">
      <PageHeader 
        title="AgentShield Interactive Sandbox" 
        description="Trigger live multi-agent orchestration events on seeded transactions and trace AgentShield decision guardrails in real-time."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT COLUMN: Selector & Event Details */}
        <div className="space-y-6 lg:col-span-1">
          
          {/* Dropdown Selector Card */}
          <div className="border border-slate-800 bg-slate-950/40 rounded-xl p-5 backdrop-blur-sm space-y-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
              <Play className="w-3.5 h-3.5 text-cyan-400" />
              Ingestion Simulator
            </h3>
            
            <div className="space-y-2">
              <label htmlFor="scenario-select" className="text-xs text-slate-400 font-medium">Select Simulated Scenario</label>
              <select
                id="scenario-select"
                value={selectedScenarioIndex}
                onChange={(e) => {
                  setSelectedScenarioIndex(Number(e.target.value));
                  setScenarioData(null);
                  setError(null);
                  setIdempotentHit(false);
                }}
                className="w-full bg-slate-900 border border-slate-800 text-slate-100 rounded-lg p-2.5 text-xs font-semibold focus:outline-none focus:border-cyan-500 cursor-pointer"
              >
                {DEMO_SCENARIOS.map((sc, i) => (
                  <option key={sc.id} value={i}>
                    {sc.name}
                  </option>
                ))}
              </select>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed italic">
              {currentScenario.details.description}
            </p>

            <button
              onClick={handleProcessEvent}
              disabled={isProcessing}
              className={`w-full py-2.5 px-4 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer border ${
                isProcessing 
                  ? 'bg-slate-900 border-slate-800 text-slate-500' 
                  : 'bg-cyan-950/20 hover:bg-cyan-950/40 text-cyan-400 border-cyan-800/40 hover:border-cyan-500 shadow-lg shadow-cyan-950/20'
              }`}
            >
              <Play className="w-4 h-4" />
              {isProcessing ? 'PROCESSING EVENT...' : 'PROCESS EVENT'}
            </button>
          </div>

          {/* Event Metadata Details Card */}
          <div className="border border-slate-800 bg-slate-950/40 rounded-xl p-5 backdrop-blur-sm space-y-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-cyan-400" />
              Source Event Details
            </h3>

            <div className="space-y-3 divide-y divide-slate-900 text-xs">
              <div className="flex justify-between items-center py-1.5 first:pt-0">
                <span className="text-slate-500">Event Type</span>
                <span className="font-mono text-cyan-400 bg-cyan-950/10 px-2 py-0.5 border border-cyan-900/30 rounded">
                  {currentScenario.event_type}
                </span>
              </div>
              <div className="flex justify-between items-center py-1.5">
                <span className="text-slate-500">Event ID</span>
                <span className="font-mono text-slate-300 truncate max-w-[150px]" title={currentScenario.event_id}>
                  {currentScenario.event_id}
                </span>
              </div>
              <div className="flex justify-between items-center py-1.5">
                <span className="text-slate-500">Customer</span>
                <span className="font-semibold text-slate-200">{currentScenario.details.customer}</span>
              </div>
              <div className="flex justify-between items-center py-1.5">
                <span className="text-slate-500">Merchant</span>
                <span className="font-semibold text-slate-200">{currentScenario.details.merchant}</span>
              </div>
              <div className="flex justify-between items-center py-1.5">
                <span className="text-slate-500">Amount</span>
                <span className="font-mono font-bold text-white">{currentScenario.details.amount}</span>
              </div>
              <div className="flex justify-between items-center py-1.5">
                <span className="text-slate-500">Location</span>
                <span className="font-semibold text-slate-200">{currentScenario.details.location}</span>
              </div>
              <div className="flex justify-between items-center py-1.5">
                <span className="text-slate-500">Status</span>
                <span className="font-semibold text-slate-300">{currentScenario.details.status}</span>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN (2 cols wide): Visual Workflow Sequence Traces */}
        <div className="lg:col-span-2 space-y-6">
          
          {isProcessing && (
            <div className="border border-slate-800 bg-slate-950/20 rounded-xl p-12 backdrop-blur-sm">
              <LoadingState message="FastAPI intercepting event... routing context to specialized agents... executing models..." />
            </div>
          )}

          {!isProcessing && isLoadingDetails && (
            <div className="border border-slate-800 bg-slate-950/20 rounded-xl p-12 backdrop-blur-sm">
              <LoadingState message="Fetching Agent proposals and Shield evaluations..." />
            </div>
          )}

          {!isProcessing && !isLoadingDetails && error && (
            <div className="border border-slate-800 bg-slate-950/20 rounded-xl p-8 backdrop-blur-sm">
              <ErrorState message={error} onRetry={handleProcessEvent} />
            </div>
          )}

          {!isProcessing && !isLoadingDetails && !error && !scenarioData && (
            <div className="border border-slate-850 bg-slate-950/10 rounded-xl p-12 text-center text-slate-500">
              <EmptyState 
                title="Sandbox Idle" 
                description="Select a demo scenario and click 'PROCESS EVENT' above to observe live guardrail traces." 
              />
            </div>
          )}

          {!isProcessing && !isLoadingDetails && !error && scenarioData && (
            <div className="space-y-6">
              
              {/* Idempotency Warning Banner */}
              {idempotentHit && (
                <div className="flex items-center gap-3 border border-amber-900/30 bg-amber-950/10 p-4 rounded-xl text-xs text-amber-300 backdrop-blur-sm">
                  <Clock className="w-5 h-5 shrink-0 text-amber-400" />
                  <div>
                    <span className="font-bold block uppercase tracking-wider text-[10px] text-amber-400 mb-0.5">Idempotent Response Triggered</span>
                    This event was previously processed. Returned the cached workflow state. No duplicate proposals, decisions, or audit committed.
                  </div>
                </div>
              )}

              {/* Orchestrator Consolidated Status */}
              {workflowMeta && (
                <div className="border border-slate-800 bg-slate-950/60 rounded-xl p-4 backdrop-blur-sm flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded bg-cyan-950/30 border border-cyan-800/40 text-cyan-400">
                      <Activity className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                        Orchestrator Workflow
                      </div>
                      <div className="text-xs font-bold text-white flex items-center gap-2">
                        <span className="text-emerald-400 font-mono">{workflowMeta.status}</span>
                        <span className="text-slate-500">•</span>
                        <span className="text-slate-300 font-normal">
                          {proposalsList.length} Agent{proposalsList.length > 1 ? 's' : ''} Evaluated
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-0.5">
                      Consolidated Final Decision
                    </div>
                    <StatusBadge status={workflowMeta.final_decision} />
                  </div>
                </div>
              )}

              {/* Multi-Agent Perspective Switcher */}
              {proposalsList.length > 1 && (
                <div className="border border-slate-800 bg-slate-950/40 rounded-xl p-3 backdrop-blur-sm flex items-center gap-3">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider pl-1 shrink-0">
                    Agent View:
                  </span>
                  <div className="flex gap-2 flex-wrap">
                    {proposalsList.map((item, idx) => (
                      <button
                        key={item.proposal.proposal_id}
                        onClick={() => handleSelectProposal(idx)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                          activeProposalIdx === idx
                            ? 'bg-cyan-950 border border-cyan-500/70 text-cyan-300 shadow-sm shadow-cyan-950/40'
                            : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        {item.agent.agent_type === 'FRAUD' && '🛡️'}
                        {item.agent.agent_type === 'RECOVERY' && '💳'}
                        {item.agent.agent_type === 'GROWTH' && '📈'}
                        <span>{item.agent.name}</span>
                        {item.agent.agent_type === 'RECOVERY' && (
                          <span className="text-[9px] bg-cyan-950 text-cyan-400 px-1 py-0.2 rounded border border-cyan-850">
                            RAG
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Main Workflow Lifecycle trace */}
              <div className="border border-slate-800 bg-slate-950/20 rounded-xl p-6 backdrop-blur-sm space-y-6">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  Control Plane Workflow Lifecycle Trace
                </h3>

                <div className="space-y-4 relative">
                  
                  {/* Step 1: Event Ingestion */}
                  <div className="flex items-start gap-4 border border-slate-900 bg-slate-950/40 p-4 rounded-lg">
                    <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400 shrink-0">
                      <Activity className="w-4 h-4 text-emerald-400" />
                    </div>
                    <div className="space-y-1">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Step 1: Event Ingestion</div>
                      <div className="font-bold text-white text-sm">
                        {currentScenario.event_type} Ingested
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {currentScenario.event_type === 'GROWTH_OPPORTUNITY'
                          ? `Ingested growth opportunity for customer ${scenarioData.event.customer} with cart value ${scenarioData.event.amount}`
                          : `Ingested ${scenarioData.event.payment_method} transaction of ${scenarioData.event.amount} | Location: ${scenarioData.event.location}`
                        }
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-center">
                    <ArrowDown className="w-4 h-4 text-slate-700" />
                  </div>

                  {/* Step 2: Agent Selection */}
                  <div className="flex items-start gap-4 border border-slate-900 bg-slate-950/40 p-4 rounded-lg">
                    <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400 shrink-0">
                      <Cpu className="w-4 h-4 text-cyan-400" />
                    </div>
                    <div className="space-y-1">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Step 2: Proposing Specialized AI Agent</div>
                      <div className="font-bold text-white text-sm">{scenarioData.agent.name}</div>
                      <div className="text-[11px] text-slate-400 leading-relaxed">
                        Type: <span className="font-mono text-cyan-400">{scenarioData.agent.agent_type}</span> | Description: {scenarioData.agent.description}
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-center">
                    <ArrowDown className="w-4 h-4 text-slate-700" />
                  </div>

                  {/* Step 3: Fraud ML (If applicable) */}
                  {isMLPresent && (
                    <>
                      <div className="flex items-start gap-4 border border-slate-900 bg-slate-950/40 p-4 rounded-lg">
                        <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400 shrink-0">
                          <Sparkles className="w-4 h-4 text-amber-400" />
                        </div>
                        <div className="space-y-2 w-full text-xs">
                          <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Step 3: Fraud ML Inference Evaluation</div>
                          
                          {mlSignal.fraud_probability !== undefined ? (
                            <div className="grid grid-cols-3 gap-4">
                              <div className="p-2 bg-slate-950 border border-slate-900 rounded">
                                <span className="text-[9px] text-slate-500 uppercase block font-bold">Fraud Probability</span>
                                <span className="font-mono font-bold text-sm text-white">{(mlSignal.fraud_probability * 100).toFixed(2)}%</span>
                              </div>
                              <div className="p-2 bg-slate-950 border border-slate-900 rounded">
                                <span className="text-[9px] text-slate-500 uppercase block font-bold">Risk Level</span>
                                <span className={`font-mono font-bold text-sm ${mlSignal.fraud_risk_level === 'HIGH' ? 'text-rose-400' : 'text-emerald-400'}`}>
                                  {mlSignal.fraud_risk_level}
                                </span>
                              </div>
                              <div className="p-2 bg-slate-950 border border-slate-900 rounded">
                                <span className="text-[9px] text-slate-500 uppercase block font-bold">Model Version</span>
                                <span className="font-mono text-sm text-slate-400">{mlSignal.ml_model_version || '1.0.0'}</span>
                              </div>
                            </div>
                          ) : (
                            <span className="text-slate-400 italic">Fraud ML Signal Not Available for this workflow event.</span>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex justify-center">
                        <ArrowDown className="w-4 h-4 text-slate-700" />
                      </div>
                    </>
                  )}

                  {/* Step 4: Agent Proposal */}
                  <div className="flex items-start gap-4 border border-slate-900 bg-slate-950/40 p-4 rounded-lg">
                    <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400 shrink-0">
                      <FileText className="w-4 h-4 text-indigo-400" />
                    </div>
                    <div className="space-y-2 w-full">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Step 4: AI Agent Proposal Plan</div>
                      
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="text-xs font-mono font-bold text-white bg-slate-900 border border-slate-850 px-2.5 py-1 rounded inline-block">
                            {scenarioData.proposal.action}
                          </div>
                          <div className="text-[10px] text-slate-500 mt-1">
                            Confidence: <span className="font-mono font-bold text-slate-300">{(Number(scenarioData.proposal.confidence) * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                        <span className="text-[10px] text-slate-400 italic">
                          Reason: {scenarioData.proposal.reason_summary}
                        </span>
                      </div>

                      {/* Evidence */}
                      {scenarioData.proposal.evidence && (
                        <div className="pt-2 border-t border-slate-900/60 flex items-center gap-1.5 flex-wrap">
                          <span className="text-[9px] text-slate-500 font-bold uppercase tracking-wider">Evidence Logs:</span>
                          {scenarioData.proposal.evidence.map((ev: string, i: number) => (
                            <span key={i} className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-950 border border-slate-900 text-slate-400">
                              {ev}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex justify-center">
                    <ArrowDown className="w-4 h-4 text-slate-700" />
                  </div>

                  {/* Step 5: Merchant Policy Checked */}
                  <div className="flex items-start gap-4 border border-slate-900 bg-slate-950/40 p-4 rounded-lg">
                    <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400 shrink-0">
                      <Settings className="w-4 h-4 text-slate-400" />
                    </div>
                    <div className="space-y-2 w-full">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Step 5: Merchant Policies Compliance (RAG Context)</div>
                      <div className="space-y-1.5">
                        {scenarioData.merchant_policies && scenarioData.merchant_policies.length > 0 ? (
                          scenarioData.merchant_policies.map((policy) => {
                            const valWrapper = policy.policy_value;
                            const cleanValue = valWrapper?.value !== undefined ? valWrapper.value : JSON.stringify(valWrapper);
                            
                            return (
                              <div key={policy.id} className="flex justify-between items-center text-xs py-1 border-b border-slate-900 last:border-b-0">
                                <span className="text-slate-400 font-medium">{policy.policy_name}</span>
                                <span className="font-mono text-white bg-slate-950 px-2 py-0.5 border border-slate-900 rounded">
                                  {policy.policy_key === 'max_discount_percent' ? `${cleanValue}%` : String(cleanValue)}
                                </span>
                              </div>
                            );
                          })
                        ) : (
                          <span className="text-slate-500 italic text-xs">No merchant policies fetched.</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-center">
                    <ArrowDown className="w-4 h-4 text-slate-700" />
                  </div>

                  {/* Step 6: AgentShield Decision */}
                  <div className="flex items-start gap-4 border border-cyan-900/30 bg-cyan-950/5 p-4 rounded-lg">
                    <div className="p-2 rounded bg-cyan-950/20 border border-cyan-800/30 text-cyan-400 shrink-0">
                      <Shield className="w-4 h-4" />
                    </div>
                    <div className="space-y-4 w-full">
                      <div className="flex justify-between items-start">
                        <div className="text-[10px] text-cyan-500 font-bold uppercase tracking-wider">Step 6: AgentShield Override Logic Evaluation</div>
                        <StatusBadge status={scenarioData.shield_decision.decision} />
                      </div>

                      {/* Final Action Enforced */}
                      {scenarioData.shield_decision.decision === 'MODIFY' ? (
                        <div className="bg-slate-950 p-4 border border-slate-900 rounded-lg flex flex-col md:flex-row items-center justify-center gap-4 text-xs">
                          <div className="text-center">
                            <span className="text-[9px] text-slate-500 font-bold uppercase block mb-1">Proposed</span>
                            <span className="font-mono text-slate-400 bg-slate-900 border border-slate-850 px-3 py-1.5 rounded inline-block">
                              {formatActionDisplay(scenarioData.proposal.action, scenarioData.shield_decision.modified_from)}
                            </span>
                          </div>
                          <ArrowRight className="w-4 h-4 text-slate-500 rotate-90 md:rotate-0" />
                          <div className="text-center">
                            <span className="text-[9px] text-cyan-500 font-bold uppercase block mb-1">Final Enforced Action</span>
                            <span className="font-mono text-emerald-400 bg-slate-900 border border-cyan-900/40 px-3 py-1.5 rounded inline-block font-bold">
                              {formatActionDisplay(scenarioData.shield_decision.final_action, scenarioData.shield_decision.final_action_parameters)}
                            </span>
                          </div>
                        </div>
                      ) : (
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase">Final Action Enforced</div>
                          <div className="text-xs font-mono font-bold text-emerald-400 bg-slate-950 border border-slate-900 px-3 py-2 rounded inline-block mt-1">
                            {formatActionDisplay(scenarioData.shield_decision.final_action, scenarioData.shield_decision.final_action_parameters)}
                          </div>
                        </div>
                      )}

                      <div className="text-xs leading-relaxed bg-slate-950/40 p-3 rounded-lg border border-slate-900">
                        <span className="text-slate-500 font-bold block mb-1">Decision Justification:</span>
                        <p className="text-slate-300">{scenarioData.shield_decision.reason}</p>
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-center">
                    <ArrowDown className="w-4 h-4 text-slate-700" />
                  </div>

                  {/* Step 7: Audit timeline */}
                  <div className="flex items-start gap-4 border border-slate-900 bg-slate-950/40 p-4 rounded-lg">
                    <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400 shrink-0">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    </div>
                    <div className="space-y-3 w-full text-xs">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Step 7: Audit Telemetry persisted</div>
                      <div className="space-y-2">
                        {scenarioData.audit_logs && scenarioData.audit_logs.length > 0 ? (
                          scenarioData.audit_logs.map((log) => (
                            <div key={log.id} className="flex justify-between items-start p-2 rounded bg-slate-950 border border-slate-900 text-slate-300">
                              <div className="flex items-center gap-1.5 font-semibold text-white">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                                {log.action}
                              </div>
                              <span className="font-mono text-[9px] text-slate-500">
                                {new Date(log.created_at).toLocaleTimeString()}
                              </span>
                            </div>
                          ))
                        ) : (
                          <div className="flex justify-between items-start p-2 rounded bg-slate-950 border border-slate-900 text-slate-300">
                            <span className="flex items-center gap-1.5 font-semibold text-white">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                              DECISION_PERSISTED
                            </span>
                            <span className="font-mono text-[9px] text-slate-500">Just Now</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                </div>
              </div>

            </div>
          )}

        </div>

      </div>
    </div>
  );
}
