'use client';

import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { EmptyState } from '@/components/shared/empty-state';
import { StatusBadge } from '@/components/shared/status-badge';
import { getDemoScenario } from '@/lib/api/client';
import { DemoScenario } from '@/types/api';
import { Play, Shield, ArrowRight, Cpu, FileText, CheckCircle2 } from 'lucide-react';

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

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Interactive Sandbox Scenarios" 
        description="Verify dynamic control plane traces (Event -> Proposing Agent -> Guardrail Policies -> Shield Decision)."
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
          {/* Main Visual Flow Trace Summary */}
          <div className="lg:col-span-2 space-y-6">
            <div className="border border-slate-800/80 bg-slate-950/20 rounded-xl p-6 backdrop-blur-sm space-y-6">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Play className="w-4 h-4 text-cyan-400" />
                Scenario Lifecycle Sequence
              </h3>

              {/* Dynamic Step Flow Diagram */}
              <div className="space-y-4 text-sm">
                {/* 1. Source Event */}
                <div className="flex items-start gap-4 border border-slate-900 bg-slate-950/40 p-4 rounded-lg">
                  <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400 shrink-0">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 font-bold uppercase tracking-wider">Step 1: Source Event Trigger</div>
                    <div className="font-bold text-white mt-1">
                      {selectedScenario === 'growth' ? 'Growth Opportunity Triggered' : `Transaction: ${scenarioData.event.external_transaction_id}`}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      {selectedScenario === 'growth' 
                        ? 'Customer Rohan Das abandoned high value cart (INR 45,000)'
                        : `Amount: INR ${scenarioData.event.amount.toLocaleString()} | Location: ${scenarioData.event.location}`
                      }
                    </div>
                  </div>
                </div>

                <div className="flex justify-center py-1">
                  <ArrowRight className="w-4 h-4 text-slate-700 rotate-90" />
                </div>

                {/* 2. Proposing Agent */}
                <div className="flex items-start gap-4 border border-slate-900 bg-slate-950/40 p-4 rounded-lg">
                  <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400 shrink-0">
                    <Cpu className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 font-bold uppercase tracking-wider">Step 2: Proposing AI Agent</div>
                    <div className="font-bold text-white mt-1">{scenarioData.agent.name}</div>
                    <div className="text-xs text-slate-400 mt-1">
                      Proposed action: <span className="font-mono text-cyan-400 font-semibold">{scenarioData.proposal.action}</span> with{' '}
                      <span className="font-bold">{(Number(scenarioData.proposal.confidence) * 100).toFixed(0)}%</span> confidence.
                    </div>
                  </div>
                </div>

                <div className="flex justify-center py-1">
                  <ArrowRight className="w-4 h-4 text-slate-700 rotate-90" />
                </div>

                {/* 3. AgentShield Policy Decision */}
                <div className="flex items-start gap-4 border border-cyan-900/30 bg-cyan-950/5 p-4 rounded-lg">
                  <div className="p-2 rounded bg-cyan-950/20 border border-cyan-800/30 text-cyan-400 shrink-0">
                    <Shield className="w-4 h-4" />
                  </div>
                  <div className="w-full">
                    <div className="flex justify-between items-start">
                      <div className="text-xs text-cyan-500 font-bold uppercase tracking-wider">Step 3: AgentShield Decision Layer</div>
                      <StatusBadge status={scenarioData.shield_decision.decision} />
                    </div>
                    <div className="font-bold text-white mt-1">
                      Executed: <span className="font-mono text-emerald-400">{scenarioData.shield_decision.final_action}</span>
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      Reason: {scenarioData.shield_decision.reason}
                    </div>
                    {scenarioData.shield_decision.modified_from && (
                      <div className="text-xs mt-2 px-2.5 py-1.5 rounded bg-amber-950/10 border border-amber-900/30 text-amber-400 font-mono">
                        Modified from: {JSON.stringify(scenarioData.shield_decision.modified_from)}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar parameters audit */}
          <div className="space-y-6">
            {/* Merchant Guardrail Policies */}
            <div className="border border-slate-800/80 bg-slate-950/20 rounded-xl p-5 backdrop-blur-sm space-y-4">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Policies Checked</h4>
              <div className="space-y-3">
                {scenarioData.merchant_policies.map((p) => (
                  <div key={p.id} className="text-xs flex items-center justify-between py-1.5 border-b border-slate-900">
                    <span className="text-slate-400 font-medium">{p.policy_name}</span>
                    <span className="font-mono text-slate-200">{JSON.stringify(p.policy_value)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Scenario Logs */}
            <div className="border border-slate-800/80 bg-slate-950/20 rounded-xl p-5 backdrop-blur-sm space-y-4">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Trace Audit Logs</h4>
              <div className="space-y-4">
                {scenarioData.audit_logs.map((log) => (
                  <div key={log.id} className="flex gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                    <div>
                      <div className="text-xs text-white font-semibold">{log.action}</div>
                      <div className="text-[10px] text-slate-500">{new Date(log.created_at).toLocaleTimeString()}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
