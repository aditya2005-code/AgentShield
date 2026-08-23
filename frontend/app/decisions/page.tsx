'use client';

import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { EmptyState } from '@/components/shared/empty-state';
import { DataTableShell } from '@/components/shared/data-table-shell';
import { StatusBadge } from '@/components/shared/status-badge';
import { DetailDrawer } from '@/components/shared/detail-drawer';
import { getDecisions, getDecisionById } from '@/lib/api/client';
import { ShieldDecision, ShieldDecisionDetail } from '@/types/api';
import { 
  Shield, 
  ArrowDown, 
  HelpCircle, 
  CheckCircle2, 
  AlertOctagon, 
  ChevronRight, 
  UserCheck, 
  Brain,
  Sliders,
  Calendar
} from 'lucide-react';

export default function DecisionsPage() {
  const [decisions, setDecisions] = useState<ShieldDecision[]>([]);
  const [selectedDecision, setSelectedDecision] = useState<ShieldDecisionDetail | null>(null);

  // Filters State
  const [decisionFilter, setDecisionFilter] = useState<string>('');
  const [humanReviewFilter, setHumanReviewFilter] = useState<string>('');

  // Page States
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const fetchDecisionsData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const isReviewRequired = humanReviewFilter === 'true' 
        ? true 
        : humanReviewFilter === 'false' 
          ? false 
          : undefined;

      const data = await getDecisions({
        decision: decisionFilter || undefined,
        requires_human_review: isReviewRequired,
        limit: 50
      });
      setDecisions(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load decisions.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDecisionsData();
  }, [decisionFilter, humanReviewFilter]);

  const handleOpenDetail = async (decisionId: string) => {
    setIsLoadingDetail(true);
    setDetailError(null);
    setSelectedDecision(null);
    setIsDrawerOpen(true);
    try {
      const detail = await getDecisionById(decisionId);
      setSelectedDecision(detail);
    } catch (err: any) {
      setDetailError(err.message || 'Failed to fetch decision details.');
    } finally {
      setIsLoadingDetail(false);
    }
  };

  // Visual helper to format actions nicely
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
    
    // Fallback
    if (params && Object.keys(params).length > 0) {
      return `${action} (${JSON.stringify(params)})`;
    }
    return action;
  };

  return (
    <div className="space-y-6">
      <PageHeader 
        title="AgentShield Decisions Log" 
        description="Audit policy evaluations and action override guards executed by the AgentShield control plane."
        action={
          <div className="flex flex-wrap items-center gap-3">
            {/* Decision Filter */}
            <div className="flex items-center gap-1.5">
              <label htmlFor="decision-select" className="text-[10px] text-slate-500 font-bold uppercase select-none">
                Shield Decision
              </label>
              <select
                id="decision-select"
                value={decisionFilter}
                onChange={(e) => setDecisionFilter(e.target.value)}
                className="bg-slate-900 border border-slate-800 text-white text-xs font-semibold rounded-lg px-2.5 py-1.5 cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-600"
              >
                <option value="">ALL DECISIONS</option>
                <option value="APPROVE">APPROVED</option>
                <option value="MODIFY">MODIFIED</option>
                <option value="ESCALATE">ESCALATED</option>
                <option value="REJECT">REJECTED</option>
              </select>
            </div>

            {/* Human Review Filter */}
            <div className="flex items-center gap-1.5">
              <label htmlFor="review-select" className="text-[10px] text-slate-500 font-bold uppercase select-none">
                Human Review
              </label>
              <select
                id="review-select"
                value={humanReviewFilter}
                onChange={(e) => setHumanReviewFilter(e.target.value)}
                className="bg-slate-900 border border-slate-800 text-white text-xs font-semibold rounded-lg px-2.5 py-1.5 cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-600"
              >
                <option value="">ALL VERIFICATIONS</option>
                <option value="true">REQUIRED</option>
                <option value="false">AUTO RESOLVED</option>
              </select>
            </div>
          </div>
        }
      />

      {isLoading && <LoadingState message="Connecting to decisions database..." />}

      {!isLoading && error && (
        <ErrorState 
          message={error} 
          onRetry={fetchDecisionsData} 
          isConnectionError={error.includes('failed') || error.includes('fetch')} 
        />
      )}

      {!isLoading && !error && decisions.length === 0 && (
        <EmptyState 
          title="No Decisions Recorded" 
          description="There are currently no AgentShield decisions recorded matching the selection filters." 
        />
      )}

      {!isLoading && !error && decisions.length > 0 && (
        <DataTableShell headers={['Decision ID', 'Decision Outcome', 'Final Action', 'Checks Count', 'Human Review', 'Decided At', 'Actions']}>
          {decisions.map((dec) => (
            <tr 
              key={dec.decision_id} 
              onClick={() => handleOpenDetail(dec.decision_id)}
              className="hover:bg-slate-900/10 cursor-pointer transition-colors"
            >
              <td className="px-6 py-4 font-mono text-xs text-cyan-400 whitespace-nowrap">
                {dec.decision_id.slice(0, 8)}...
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <StatusBadge status={dec.decision} />
              </td>
              <td className="px-6 py-4 font-mono font-bold text-white whitespace-nowrap">{dec.final_action}</td>
              <td className="px-6 py-4 text-xs text-slate-300 whitespace-nowrap">
                {dec.checks.length} Rule(s) Checked
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                  dec.requires_human_review 
                    ? 'bg-amber-950/30 text-amber-400 border-amber-800/40' 
                    : 'bg-slate-800/60 text-slate-400 border-slate-700/60'
                }`}>
                  {dec.requires_human_review ? 'REQUIRED' : 'AUTO_RESOLVED'}
                </span>
              </td>
              <td className="px-6 py-4 text-xs text-slate-400 whitespace-nowrap">
                {new Date(dec.created_at).toLocaleString()}
              </td>
              <td className="px-6 py-4 text-right whitespace-nowrap">
                <button 
                  onClick={(e) => { e.stopPropagation(); handleOpenDetail(dec.decision_id); }}
                  className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
                  aria-label={`View details of decision ${dec.decision_id}`}
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </td>
            </tr>
          ))}
        </DataTableShell>
      )}

      {/* Decisions detail slide-over panel */}
      <DetailDrawer 
        isOpen={isDrawerOpen} 
        onClose={() => setIsDrawerOpen(false)}
        title={selectedDecision ? `Shield Decision Details` : 'Querying Shield Decision Details'}
      >
        {isLoadingDetail && (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mb-3" />
            <span className="text-xs">Connecting shield rules with dynamic agent proposal...</span>
          </div>
        )}

        {detailError && (
          <div className="p-4 bg-rose-950/10 border border-rose-900/30 text-rose-400 text-xs rounded-lg">
            {detailError}
          </div>
        )}

        {!isLoadingDetail && !detailError && selectedDecision && (
          <div className="space-y-6">
            
            {/* Core Outcome Panel */}
            <div className="border border-slate-800 bg-slate-900/10 rounded-xl p-5 space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Shield Decision Outcome</span>
                  <div className="mt-1.5">
                    <StatusBadge status={selectedDecision.decision} />
                  </div>
                </div>
                
                <div className="text-right">
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest block">Human Review</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 border rounded uppercase mt-1 inline-block ${
                    selectedDecision.requires_human_review 
                      ? 'bg-amber-950/30 text-amber-400 border-amber-800/40' 
                      : 'bg-slate-800/60 text-slate-400 border-slate-700/60'
                  }`}>
                    {selectedDecision.requires_human_review ? 'REQUIRED' : 'AUTO_RESOLVED'}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs pt-2 border-t border-slate-900">
                <div className="flex items-center gap-2">
                  <Brain className="w-4 h-4 text-slate-500" />
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase">Proposing Agent</div>
                    <div className="text-white font-medium">
                      {selectedDecision.agent ? selectedDecision.agent.name : 'Unknown Agent'}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-slate-500" />
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase">Evaluation Date</div>
                    <div className="text-white font-medium">
                      {new Date(selectedDecision.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Action Modification Comparison Box */}
            <div className="space-y-3">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Policy Override Actions Comparison</h4>
              
              {selectedDecision.decision === 'MODIFY' ? (
                <div className="border border-cyan-900/30 bg-cyan-950/5 rounded-xl p-5 flex flex-col items-center justify-center space-y-4">
                  
                  {/* Original Proposed Action */}
                  <div className="w-full text-center">
                    <span className="text-[10px] text-slate-500 font-semibold uppercase block">Original Proposed Action</span>
                    <div className="text-sm font-bold text-slate-400 bg-slate-950 border border-slate-900 rounded px-4 py-2 mt-1 font-mono inline-block">
                      {formatActionDisplay(selectedDecision.proposal.action, selectedDecision.modified_from)}
                    </div>
                  </div>

                  {/* Transition Indicator */}
                  <div className="flex flex-col items-center">
                    <div className="p-1.5 rounded-full bg-cyan-950/30 border border-cyan-800/40 text-cyan-400 animate-pulse">
                      <ArrowDown className="w-4 h-4" />
                    </div>
                  </div>

                  {/* Adjusted Final Action */}
                  <div className="w-full text-center">
                    <span className="text-[10px] text-cyan-500 font-bold uppercase block">Adjusted Final Action</span>
                    <div className="text-sm font-extrabold text-emerald-400 bg-slate-950 border border-cyan-900/40 rounded px-4 py-2 mt-1 font-mono inline-block">
                      {formatActionDisplay(selectedDecision.final_action, selectedDecision.final_action_parameters)}
                    </div>
                  </div>

                </div>
              ) : (
                <div className="border border-slate-900 bg-slate-950/40 rounded-xl p-4 text-xs space-y-3">
                  <div>
                    <span className="text-slate-500 font-bold block mb-1">Final Executed Action</span>
                    <span className="font-mono text-white bg-slate-950 border border-slate-900 px-3 py-1.5 rounded font-semibold inline-block">
                      {formatActionDisplay(selectedDecision.final_action, selectedDecision.final_action_parameters)}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Shield Evaluation Reason */}
            <div className="space-y-3">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Shield Override Logic</h4>
              <div className="border border-slate-900 bg-slate-950/40 rounded-xl p-4 text-xs leading-relaxed text-slate-300">
                <span className="text-slate-500 font-bold block mb-1">Decision Reason</span>
                <p className="bg-slate-950/60 border border-slate-900 p-3 rounded-lg">
                  {selectedDecision.reason}
                </p>
              </div>
            </div>

            {/* Shield Evaluation Rule Checks */}
            <div className="space-y-3">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Enforced Guardrail Checks</h4>
              <div className="space-y-2">
                {selectedDecision.checks && selectedDecision.checks.length > 0 ? (
                  selectedDecision.checks.map((chk, index) => (
                    <div key={index} className="flex items-start justify-between p-3 rounded-xl bg-slate-950/40 border border-slate-900 text-xs">
                      <div>
                        <div className="font-bold text-white flex items-center gap-1.5">
                          <Sliders className="w-3.5 h-3.5 text-cyan-500" />
                          {chk.name}
                        </div>
                        <p className="text-slate-400 text-[11px] mt-1 leading-relaxed">{chk.message}</p>
                      </div>
                      <span className={`text-[9px] font-bold px-2 py-0.5 rounded border uppercase ${
                        chk.status === 'PASSED' 
                          ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800/50' 
                          : 'bg-rose-950/40 text-rose-400 border-rose-800/50'
                      }`}>
                        {chk.status}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="text-slate-500 italic text-xs">No individual security rule checks were logged for this decision.</div>
                )}
              </div>
            </div>

          </div>
        )}
      </DetailDrawer>
    </div>
  );
}
