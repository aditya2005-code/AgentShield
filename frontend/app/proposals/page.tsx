'use client';

import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { EmptyState } from '@/components/shared/empty-state';
import { DataTableShell } from '@/components/shared/data-table-shell';
import { StatusBadge } from '@/components/shared/status-badge';
import { DetailDrawer } from '@/components/shared/detail-drawer';
import { getProposals, getProposalById, getAgents, getMerchants } from '@/lib/api/client';
import { ActionProposal, ProposalDetail, Agent, Merchant } from '@/types/api';
import { 
  Cpu, 
  Building, 
  AlertTriangle, 
  Sliders, 
  HelpCircle, 
  ExternalLink,
  ShieldCheck,
  TrendingDown,
  Calendar,
  Layers
} from 'lucide-react';

export default function ProposalsPage() {
  const [proposals, setProposals] = useState<ActionProposal[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [merchants, setMerchants] = useState<Merchant[]>([]);
  const [selectedProposal, setSelectedProposal] = useState<ProposalDetail | null>(null);

  // Filters State
  const [agentFilter, setAgentFilter] = useState<string>('');
  const [merchantFilter, setMerchantFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('');

  // Page States
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const fetchFilters = async () => {
    try {
      const [agentsData, merchantsData] = await Promise.all([
        getAgents(),
        getMerchants()
      ]);
      setAgents(agentsData);
      setMerchants(merchantsData);
    } catch (err) {
      console.error('Failed to load filters metadata:', err);
    }
  };

  const fetchProposalsData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getProposals({
        agent_id: agentFilter || undefined,
        merchant_id: merchantFilter || undefined,
        status: statusFilter || undefined,
        event_type: eventTypeFilter || undefined,
        limit: 50
      });
      setProposals(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load proposals.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFilters();
  }, []);

  useEffect(() => {
    fetchProposalsData();
  }, [agentFilter, merchantFilter, statusFilter, eventTypeFilter]);

  const handleOpenDetail = async (propId: string) => {
    setIsLoadingDetail(true);
    setDetailError(null);
    setSelectedProposal(null);
    setIsDrawerOpen(true);
    try {
      const detail = await getProposalById(propId);
      setSelectedProposal(detail);
    } catch (err: any) {
      setDetailError(err.message || 'Failed to fetch proposal details.');
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const getImpactBadgeStyle = (impact: string) => {
    switch (impact.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-rose-950/30 text-rose-400 border-rose-800/40';
      case 'HIGH':
        return 'bg-orange-950/30 text-orange-400 border-orange-800/40';
      case 'MEDIUM':
        return 'bg-amber-950/30 text-amber-400 border-amber-800/40';
      default:
        return 'bg-slate-800/50 text-slate-400 border-slate-700/40';
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Agent Action Proposals" 
        description="Verify and audit operational actions proposed by Fraud, Recovery, and Growth AI agents."
        action={
          <div className="flex flex-wrap items-center gap-3">
            {/* Agent Select */}
            <div className="flex items-center gap-1.5">
              <label htmlFor="agent-select" className="text-[10px] text-slate-500 font-bold uppercase select-none">
                Agent
              </label>
              <select
                id="agent-select"
                value={agentFilter}
                onChange={(e) => setAgentFilter(e.target.value)}
                className="bg-slate-900 border border-slate-800 text-white text-xs font-semibold rounded-lg px-2.5 py-1.5 cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-600"
              >
                <option value="">ALL AGENTS</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Merchant Select */}
            <div className="flex items-center gap-1.5">
              <label htmlFor="merchant-select" className="text-[10px] text-slate-500 font-bold uppercase select-none">
                Merchant
              </label>
              <select
                id="merchant-select"
                value={merchantFilter}
                onChange={(e) => setMerchantFilter(e.target.value)}
                className="bg-slate-900 border border-slate-800 text-white text-xs font-semibold rounded-lg px-2.5 py-1.5 cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-600"
              >
                <option value="">ALL MERCHANTS</option>
                {merchants.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Status Select */}
            <div className="flex items-center gap-1.5">
              <label htmlFor="status-select" className="text-[10px] text-slate-500 font-bold uppercase select-none">
                Status
              </label>
              <select
                id="status-select"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-900 border border-slate-800 text-white text-xs font-semibold rounded-lg px-2.5 py-1.5 cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-600"
              >
                <option value="">ALL STATUSES</option>
                <option value="PENDING">PENDING</option>
                <option value="REVIEWED">REVIEWED</option>
                <option value="EXECUTED">EXECUTED</option>
                <option value="REJECTED">REJECTED</option>
              </select>
            </div>
          </div>
        }
      />

      {isLoading && <LoadingState message="Connecting to proposals database..." />}

      {!isLoading && error && (
        <ErrorState 
          message={error} 
          onRetry={fetchProposalsData} 
          isConnectionError={error.includes('failed') || error.includes('fetch')} 
        />
      )}

      {!isLoading && !error && proposals.length === 0 && (
        <EmptyState 
          title="No Proposals Found" 
          description="There are currently no action proposals recorded in the database matching the criteria." 
        />
      )}

      {!isLoading && !error && proposals.length > 0 && (
        <DataTableShell headers={['Agent', 'Event Type', 'Proposed Action', 'Confidence', 'Fin. Impact', 'Cust. Impact', 'Status', 'Proposed At', 'Actions']}>
          {proposals.map((prop) => {
            // Find corresponding agent name
            const agentObj = agents.find(a => a.id === prop.agent_id);
            const agentLabel = agentObj ? agentObj.name : 'Unknown Agent';

            return (
              <tr 
                key={prop.proposal_id} 
                onClick={() => handleOpenDetail(prop.proposal_id)}
                className="hover:bg-slate-900/10 cursor-pointer transition-colors"
              >
                <td className="px-6 py-4 font-bold text-white whitespace-nowrap">{agentLabel}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-850 text-slate-300">
                    {prop.event_type}
                  </span>
                </td>
                <td className="px-6 py-4 font-mono font-semibold text-cyan-400 whitespace-nowrap">{prop.action}</td>
                <td className="px-6 py-4 font-mono text-xs text-slate-300 whitespace-nowrap">
                  {(Number(prop.confidence) * 100).toFixed(0)}%
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`text-[10px] font-bold px-2 py-0.5 border rounded uppercase ${getImpactBadgeStyle(prop.financial_impact)}`}>
                    {prop.financial_impact}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`text-[10px] font-bold px-2 py-0.5 border rounded uppercase ${getImpactBadgeStyle(prop.customer_impact)}`}>
                    {prop.customer_impact}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <StatusBadge status={prop.status} />
                </td>
                <td className="px-6 py-4 text-xs text-slate-400 whitespace-nowrap">
                  {new Date(prop.created_at).toLocaleString()}
                </td>
                <td className="px-6 py-4 text-right whitespace-nowrap">
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleOpenDetail(prop.proposal_id); }}
                    className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
                    aria-label={`View details of proposal ${prop.proposal_id}`}
                  >
                    <Sliders className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            );
          })}
        </DataTableShell>
      )}

      {/* Slide-over Detail Drawer */}
      <DetailDrawer 
        isOpen={isDrawerOpen} 
        onClose={() => setIsDrawerOpen(false)}
        title={selectedProposal ? `Action Proposal Audit Details` : 'Querying Proposal Details'}
      >
        {isLoadingDetail && (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mb-3" />
            <span className="text-xs">Connecting agent logs with active override status...</span>
          </div>
        )}

        {detailError && (
          <div className="p-4 bg-rose-950/10 border border-rose-900/30 text-rose-400 text-xs rounded-lg">
            {detailError}
          </div>
        )}

        {!isLoadingDetail && !detailError && selectedProposal && (
          <div className="space-y-6">
            
            {/* Core Info */}
            <div className="border border-slate-800 bg-slate-900/10 rounded-xl p-5 space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Proposed Action</span>
                  <h3 className="text-lg font-mono font-bold text-white mt-1">
                    {selectedProposal.proposal.action}
                  </h3>
                </div>
                <StatusBadge status={selectedProposal.proposal.status} />
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs pt-2">
                <div className="flex items-center gap-2 border-b border-slate-900 pb-2">
                  <Cpu className="w-4 h-4 text-slate-500" />
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase">Agent Source</div>
                    <div className="text-white font-medium">{selectedProposal.agent.name}</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2 border-b border-slate-900 pb-2">
                  <Building className="w-4 h-4 text-slate-500" />
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase">Merchant</div>
                    <div className="text-white font-medium">{selectedProposal.merchant.name}</div>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <Layers className="w-4 h-4 text-slate-500" />
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase">Trigger Event Type</div>
                    <div className="text-white font-mono">{selectedProposal.proposal.event_type}</div>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <Calendar className="w-4 h-4 text-slate-500" />
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase">Confidence Score</div>
                    <div className="text-white font-mono">{(Number(selectedProposal.proposal.confidence) * 100).toFixed(0)}%</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Evidence & Reason Block */}
            <div className="space-y-3.5">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Decision Evidence & Context</h4>
              
              <div className="border border-slate-900 bg-slate-950/40 rounded-xl p-4 space-y-4 text-xs">
                <div>
                  <div className="text-slate-500 font-bold mb-1.5">Reason Summary</div>
                  <p className="text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-900">
                    {selectedProposal.proposal.reason_summary}
                  </p>
                </div>

                <div>
                  <div className="text-slate-500 font-bold mb-2">Evidence Indicators</div>
                  <div className="flex flex-wrap gap-2">
                    {Array.isArray(selectedProposal.proposal.evidence) ? (
                      selectedProposal.proposal.evidence.map((ev: string, idx: number) => (
                        <span key={idx} className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded border border-slate-800 bg-slate-900 text-slate-300">
                          {ev}
                        </span>
                      ))
                    ) : (
                      <span className="text-slate-500 italic">No structured evidence tags recorded.</span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Action Parameters Block */}
            <div className="space-y-3.5">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Proposed Action Parameters</h4>
              <div className="border border-slate-900 bg-slate-950/40 rounded-xl p-4 text-xs">
                {selectedProposal.proposal.action_parameters && Object.keys(selectedProposal.proposal.action_parameters).length > 0 ? (
                  <div className="space-y-1.5 divide-y divide-slate-900">
                    {Object.entries(selectedProposal.proposal.action_parameters).map(([key, val]) => (
                      <div key={key} className="flex justify-between py-1.5 first:pt-0">
                        <span className="text-slate-400 font-mono">{key}</span>
                        <span className="text-white font-bold font-mono">
                          {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-slate-500 italic">This action does not contain custom operational parameters.</div>
                )}
              </div>
            </div>

            {/* Associated Shield Decision */}
            <div className="space-y-3.5">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">AgentShield Guardrail Verification</h4>
              
              {selectedProposal.shield_decision ? (
                <div className="border border-cyan-900/30 bg-cyan-950/5 rounded-xl p-4 space-y-4 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400 font-medium">Evaluation Decision</span>
                    <StatusBadge status={selectedProposal.shield_decision.decision} />
                  </div>
                  
                  <div>
                    <span className="text-slate-500 font-bold block mb-1">Authorization Check Reason</span>
                    <p className="text-slate-300 bg-slate-950/40 p-3 rounded-lg border border-slate-900 leading-relaxed">
                      {selectedProposal.shield_decision.reason}
                    </p>
                  </div>

                  {/* Shield Policy Checks List */}
                  {selectedProposal.shield_decision.checks && selectedProposal.shield_decision.checks.length > 0 && (
                    <div>
                      <span className="text-slate-500 font-bold block mb-2">Policies Evaluated</span>
                      <div className="space-y-2">
                        {selectedProposal.shield_decision.checks.map((chk, index) => (
                          <div key={index} className="flex items-start justify-between p-2 rounded bg-slate-950/60 border border-slate-900">
                            <div>
                              <div className="font-semibold text-white">{chk.name || (chk.check ? chk.check.replace(/_/g, ' ').toUpperCase() : 'Guardrail Check')}</div>
                              <div className="text-[10px] text-slate-400 mt-0.5">{chk.message || chk.reason}</div>
                            </div>
                            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
                              chk.status === 'PASSED' 
                                ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-800/40'
                                : 'bg-rose-950/40 text-rose-400 border border-rose-800/40'
                            }`}>
                              {chk.status}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex justify-between items-center border-t border-slate-900 pt-3 text-[10px]">
                    <span className="text-slate-500">Requires Human Review</span>
                    <span className={`font-bold uppercase ${selectedProposal.shield_decision.requires_human_review ? 'text-amber-400' : 'text-slate-400'}`}>
                      {selectedProposal.shield_decision.requires_human_review ? 'REQUIRED' : 'AUTO_RESOLVED'}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="border border-dashed border-slate-800 bg-slate-900/5 rounded-xl p-4 text-center text-xs text-slate-500">
                  This proposal has not been evaluated by the AgentShield guardrail system.
                </div>
              )}
            </div>

          </div>
        )}
      </DetailDrawer>
    </div>
  );
}
