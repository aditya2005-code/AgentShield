'use client';

import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { EmptyState } from '@/components/shared/empty-state';
import { StatusBadge } from '@/components/shared/status-badge';
import { getDemoScenario } from '@/lib/api/client';
import { DemoScenario } from '@/types/api';
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
  TrendingDown,
  Layers,
  Coins
} from 'lucide-react';

export default function DemoPage() {
  const [selectedScenario, setSelectedScenario] = useState<'fraud' | 'recovery' | 'growth'>('fraud');
  const [scenarioData, setScenarioData] = useState<DemoScenario | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchScenarioData = async (type: 'fraud' | 'recovery' | 'growth') => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getDemoScenario(type);
      setScenarioData(data);
    } catch (err: any) {
      setError(err.message || `Failed to load ${type} scenario.`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchScenarioData(selectedScenario);
  }, [selectedScenario]);

  // Display value formatting helper
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

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Interactive Sandbox Scenarios" 
        description="Verify dynamic control plane traces (Event -> Proposing Agent -> Action Proposal -> Policies -> Decision -> Audit Log)."
        action={
          <div className="flex bg-slate-900/60 p-1 border border-slate-800 rounded-lg">
            {(['fraud', 'recovery', 'growth'] as const).map((type) => (
              <button
                key={type}
                onClick={() => setSelectedScenario(type)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                  selectedScenario === type
                    ? 'bg-slate-800 text-white shadow-sm border border-slate-700'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {type.toUpperCase()}
              </button>
            ))}
          </div>
        }
      />

      {isLoading && <LoadingState message={`Assembling dynamic ${selectedScenario} scenario traces...`} />}

      {!isLoading && error && (
        <ErrorState 
          message={error} 
          onRetry={() => fetchScenarioData(selectedScenario)} 
          isConnectionError={error.includes('failed') || error.includes('fetch')} 
        />
      )}

      {!isLoading && !error && !scenarioData && (
        <EmptyState 
          title="Scenario Unavailable" 
          description="Seeded database records for this scenario could not be assembled." 
        />
      )}

      {!isLoading && !error && scenarioData && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Main Visual Flow Trace Sequence */}
          <div className="lg:col-span-2 space-y-4">
            <div className="border border-slate-800/80 bg-slate-950/20 rounded-xl p-6 backdrop-blur-sm space-y-6">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Play className="w-4 h-4 text-cyan-400" />
                Control Plane Decision Lifecycle Trace
              </h3>

              {/* Vertical Step Sequence Diagram */}
              <div className="space-y-4 relative">
                
                {/* 1. Source Event */}
                <div className="flex items-start gap-4 border border-slate-900 bg-slate-950/40 p-4 rounded-lg">
                  <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400 shrink-0">
                    <Activity className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="space-y-1">
                    <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Step 1: Ingested Source Event</div>
                    <div className="font-bold text-white text-sm">
                      {selectedScenario === 'growth' 
                        ? 'GROWTH_OPPORTUNITY Ingested' 
                        : `TRANSACTION Ingested: ${scenarioData.event.external_transaction_id}`}
                    </div>
                    <div className="text-[11px] text-slate-400">
                      {selectedScenario === 'growth' 
                        ? `Customer ${scenarioData.event.details?.customer_name} abandoned cart worth INR ${scenarioData.event.details?.value?.toLocaleString()}`
                        : `Amount: INR ${scenarioData.event.amount?.toLocaleString()} | IP Location: ${scenarioData.event.location} | Method: ${scenarioData.event.payment_method}`
                      }
                    </div>
                  </div>
                </div>

                <div className="flex justify-center">
                  <ArrowDown className="w-4 h-4 text-slate-700" />
                </div>

                {/* 2. Proposing Agent */}
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

                {/* 3. Action Proposal */}
                <div className="flex items-start gap-4 border border-slate-900 bg-slate-950/40 p-4 rounded-lg">
                  <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400 shrink-0">
                    <FileText className="w-4 h-4 text-indigo-400" />
                  </div>
                  <div className="space-y-2 w-full">
                    <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Step 3: Proposed Action Plan</div>
                    
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

                    {/* Evidence Indicators */}
                    {scenarioData.proposal.evidence && (
                      <div className="pt-2 border-t border-slate-900/60 flex items-center gap-1.5 flex-wrap">
                        <span className="text-[9px] text-slate-500 font-bold uppercase tracking-wider">Evidence:</span>
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

                {/* 4. Merchant Context / Policies */}
                <div className="flex items-start gap-4 border border-slate-900 bg-slate-950/40 p-4 rounded-lg">
                  <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400 shrink-0">
                    <Settings className="w-4 h-4 text-slate-400" />
                  </div>
                  <div className="space-y-2 w-full">
                    <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Step 4: Merchant Policies Checked</div>
                    <div className="space-y-1.5">
                      {scenarioData.merchant_policies.map((policy) => {
                        // Check if this policy matches key terms in our checks to highlight
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
                      })}
                    </div>
                  </div>
                </div>

                <div className="flex justify-center">
                  <ArrowDown className="w-4 h-4 text-slate-700" />
                </div>

                {/* 5. AgentShield Decision */}
                <div className="flex items-start gap-4 border border-cyan-900/30 bg-cyan-950/5 p-4 rounded-lg">
                  <div className="p-2 rounded bg-cyan-950/20 border border-cyan-800/30 text-cyan-400 shrink-0">
                    <Shield className="w-4 h-4" />
                  </div>
                  <div className="space-y-4 w-full">
                    <div className="flex justify-between items-start">
                      <div className="text-[10px] text-cyan-500 font-bold uppercase tracking-wider">Step 5: AgentShield Override Logic Evaluation</div>
                      <StatusBadge status={scenarioData.shield_decision.decision} />
                    </div>

                    {/* Action Flow */}
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
                          <span className="text-[9px] text-cyan-500 font-bold uppercase block mb-1">Final Action</span>
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
                      <span className="text-slate-500 font-bold block mb-1">Shield Verification Notes:</span>
                      <p className="text-slate-300">{scenarioData.shield_decision.reason}</p>
                    </div>
                  </div>
                </div>

                <div className="flex justify-center">
                  <ArrowDown className="w-4 h-4 text-slate-700" />
                </div>

                {/* 6. Audit History */}
                <div className="flex items-start gap-4 border border-slate-900 bg-slate-950/40 p-4 rounded-lg">
                  <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400 shrink-0">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="space-y-3 w-full text-xs">
                    <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Step 6: Control Plane Telemetry Commit</div>
                    <div className="space-y-2">
                      {scenarioData.audit_logs.map((log) => (
                        <div key={log.id} className="flex justify-between items-start p-2 rounded bg-slate-950 border border-slate-900 text-slate-300">
                          <div className="flex items-center gap-1.5 font-semibold text-white">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                            {log.action}
                          </div>
                          <span className="font-mono text-[9px] text-slate-500">
                            {new Date(log.created_at).toLocaleTimeString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </div>

          {/* Right Col: Technical Sandbox Parameters Panel */}
          <div className="space-y-6">
            
            {/* Rule Checks Breakdown */}
            <div className="border border-slate-800/80 bg-slate-950/20 rounded-xl p-5 backdrop-blur-sm space-y-4">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1">
                <Shield className="w-3.5 h-3.5 text-cyan-400" />
                Policy Checks Executed
              </h4>
              <div className="space-y-3.5">
                {scenarioData.shield_decision.checks && scenarioData.shield_decision.checks.length > 0 ? (
                  scenarioData.shield_decision.checks.map((chk, index) => (
                    <div key={index} className="p-3 bg-slate-950/60 border border-slate-900 rounded-lg text-xs space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="font-bold text-white">{chk.name}</span>
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 border rounded uppercase ${
                          chk.status === 'PASSED' 
                            ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800/40' 
                            : 'bg-rose-950/40 text-rose-400 border-rose-800/40'
                        }`}>
                          {chk.status}
                        </span>
                      </div>
                      <p className="text-slate-400 text-[11px] leading-relaxed">{chk.message}</p>
                    </div>
                  ))
                ) : (
                  <div className="text-slate-500 italic text-xs">No checklist rules recorded for this event.</div>
                )}
              </div>
            </div>

            {/* Sandbox Operations Metadata */}
            <div className="border border-slate-800/80 bg-slate-950/20 rounded-xl p-5 backdrop-blur-sm space-y-4">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1">
                <Settings className="w-3.5 h-3.5 text-cyan-400" />
                Simulation Parameters
              </h4>
              <div className="space-y-2.5 divide-y divide-slate-900 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Merchant Profile</span>
                  <span className="font-semibold text-slate-200">VeloCart Electronics</span>
                </div>
                <div className="flex justify-between items-center pt-2">
                  <span className="text-slate-500">Shield Action Mode</span>
                  <span className="font-semibold text-emerald-400">ENFORCING</span>
                </div>
                <div className="flex justify-between items-center pt-2">
                  <span className="text-slate-500">Simulation Status</span>
                  <span className="font-semibold text-white">REPLICATED FROM DATABASE</span>
                </div>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
