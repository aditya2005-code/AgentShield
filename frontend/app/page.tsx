'use client';

import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { StatusBadge } from '@/components/shared/status-badge';
import { 
  getAgents, 
  getTransactions, 
  getProposals, 
  getDecisions, 
  getAuditLogs 
} from '@/lib/api/client';
import { Agent, Transaction, ActionProposal, ShieldDecision, AuditLog } from '@/types/api';
import { 
  Shield, 
  Cpu, 
  Activity, 
  ArrowRight, 
  FileText, 
  Settings, 
  Users, 
  CheckCircle, 
  ListFilter 
} from 'lucide-react';
import Link from 'next/link';

export default function Dashboard() {
  const [data, setData] = useState<{
    agents: Agent[];
    transactions: Transaction[];
    proposals: ActionProposal[];
    decisions: ShieldDecision[];
    auditLogs: AuditLog[];
  } | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [agents, transactions, proposals, decisions, auditLogs] = await Promise.all([
        getAgents(),
        getTransactions({ limit: 100 }),
        getProposals({ limit: 100 }),
        getDecisions({ limit: 100 }),
        getAuditLogs({ limit: 100 })
      ]);
      setData({ agents, transactions, proposals, decisions, auditLogs });
    } catch (err: any) {
      setError(err.message || 'Failed to fetch dashboard telemetry data.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (isLoading) {
    return <LoadingState message="Collecting control plane telemetry and system states..." />;
  }

  if (error || !data) {
    return (
      <div className="py-12">
        <ErrorState 
          message={error || 'Telemetry data could not be collected.'} 
          onRetry={fetchDashboardData} 
          isConnectionError={error?.includes('failed') || error?.includes('fetch')} 
        />
      </div>
    );
  }

  const { agents, transactions, proposals, decisions, auditLogs } = data;

  // Calculate stats
  const totalAgents = agents.length;
  const activeAgents = agents.filter(a => a.status === 'ACTIVE').length;
  const totalTransactions = transactions.length;
  const totalProposals = proposals.length;
  const totalDecisions = decisions.length;
  const totalAuditEvents = auditLogs.length;

  // Decision breakdown
  const decisionsBreakdown = {
    APPROVE: decisions.filter(d => d.decision === 'APPROVE').length,
    MODIFY: decisions.filter(d => d.decision === 'MODIFY').length,
    ESCALATE: decisions.filter(d => d.decision === 'ESCALATE').length,
    REJECT: decisions.filter(d => d.decision === 'REJECT').length,
  };

  // Find system agents
  const fraudAgent = agents.find(a => a.agent_key === 'fraud_agent');
  const recoveryAgent = agents.find(a => a.agent_key === 'recovery_agent');
  const growthAgent = agents.find(a => a.agent_key === 'growth_agent');

  return (
    <div className="space-y-8">
      <PageHeader 
        title="Control Plane Overview" 
        description="Centralized deterministic authorization and telemetry metrics for all financial AI agents."
      />

      {/* Metrics Section */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        <div className="border border-slate-800 bg-slate-900/10 rounded-xl p-4 backdrop-blur-sm relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-[2px] bg-cyan-500" />
          <div className="text-slate-500 font-bold uppercase tracking-wider text-[10px] mb-1.5 flex justify-between">
            <span>Agents</span>
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-2xl font-black text-white">{activeAgents} <span className="text-xs font-normal text-slate-500">/ {totalAgents}</span></div>
          <div className="text-[10px] text-slate-400 mt-1">Active Agents</div>
        </div>

        <div className="border border-slate-800 bg-slate-900/10 rounded-xl p-4 backdrop-blur-sm relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-[2px] bg-emerald-500" />
          <div className="text-slate-500 font-bold uppercase tracking-wider text-[10px] mb-1.5 flex justify-between">
            <span>Transactions</span>
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-white">{totalTransactions}</div>
          <div className="text-[10px] text-slate-400 mt-1">Ingested Stream</div>
        </div>

        <div className="border border-slate-800 bg-slate-900/10 rounded-xl p-4 backdrop-blur-sm relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-[2px] bg-indigo-500" />
          <div className="text-slate-500 font-bold uppercase tracking-wider text-[10px] mb-1.5 flex justify-between">
            <span>Proposals</span>
            <FileText className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="text-2xl font-black text-white">{totalProposals}</div>
          <div className="text-[10px] text-slate-400 mt-1">Agent Action Plans</div>
        </div>

        <div className="border border-slate-800 bg-slate-900/10 rounded-xl p-4 backdrop-blur-sm relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-[2px] bg-purple-500" />
          <div className="text-slate-500 font-bold uppercase tracking-wider text-[10px] mb-1.5 flex justify-between">
            <span>Decisions</span>
            <Shield className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <div className="text-2xl font-black text-white">{totalDecisions}</div>
          <div className="text-[10px] text-slate-400 mt-1">Shield Evaluations</div>
        </div>

        <div className="border border-slate-800 bg-slate-900/10 rounded-xl p-4 backdrop-blur-sm relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-[2px] bg-amber-500" />
          <div className="text-slate-500 font-bold uppercase tracking-wider text-[10px] mb-1.5 flex justify-between">
            <span>Audit Events</span>
            <ListFilter className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-2xl font-black text-white">{totalAuditEvents}</div>
          <div className="text-[10px] text-slate-400 mt-1">Audit Records</div>
        </div>

        <div className="border border-slate-800 bg-slate-900/10 rounded-xl p-4 backdrop-blur-sm relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-[2px] bg-emerald-500" />
          <div className="text-slate-500 font-bold uppercase tracking-wider text-[10px] mb-1.5 flex justify-between">
            <span>Shield Mode</span>
            <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-white">ACTIVE</div>
          <div className="text-[10px] text-slate-400 mt-1">Guardrails Enforced</div>
        </div>
      </div>

      {/* Main Grid: System Agents & Decision Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Col (2 cols): System Agents & Recent Activity */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* System Agents Registry Section */}
          <div className="border border-slate-800/80 bg-slate-950/20 rounded-xl p-6 backdrop-blur-sm space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Cpu className="w-4 h-4 text-cyan-400" />
                Registered System Agents
              </h3>
              <Link href="/agents" className="text-xs text-cyan-400 hover:underline flex items-center gap-0.5">
                Manage Registry <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { key: 'fraud_agent', fallbackName: 'Fraud Detection Agent', fallbackDesc: 'Analyzes transaction risk using ML and LLM investigation.', type: 'FRAUD', data: fraudAgent },
                { key: 'recovery_agent', fallbackName: 'Payment Recovery Agent', fallbackDesc: 'Handles dunning sequences and payment retry strategies.', type: 'RECOVERY', data: recoveryAgent },
                { key: 'growth_agent', fallbackName: 'Growth Incentives Agent', fallbackDesc: 'Decides risk-adjusted promotions and limits for customers.', type: 'GROWTH', data: growthAgent }
              ].map((agentConfig) => {
                const name = agentConfig.data?.name || agentConfig.fallbackName;
                const desc = agentConfig.data?.description || agentConfig.fallbackDesc;
                const status = agentConfig.data?.status || 'INACTIVE';
                const type = agentConfig.data?.agent_type || agentConfig.type;
                
                let typeColor = 'text-rose-400 bg-rose-950/20 border-rose-900/30';
                if (type === 'RECOVERY') typeColor = 'text-blue-400 bg-blue-950/20 border-blue-900/30';
                if (type === 'GROWTH') typeColor = 'text-emerald-400 bg-emerald-950/20 border-emerald-900/30';

                return (
                  <div key={agentConfig.key} className="border border-slate-900 bg-slate-950/40 rounded-lg p-4 flex flex-col justify-between space-y-3">
                    <div>
                      <div className="flex justify-between items-start mb-1">
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 border rounded uppercase ${typeColor}`}>
                          {type}
                        </span>
                        <span className={`w-2 h-2 rounded-full ${status === 'ACTIVE' ? 'bg-emerald-500' : 'bg-slate-700'}`} />
                      </div>
                      <h4 className="font-bold text-white text-xs mt-1.5">{name}</h4>
                      <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Recent Agent Activity */}
          <div className="border border-slate-800/80 bg-slate-950/20 rounded-xl p-6 backdrop-blur-sm space-y-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              Recent Agent Activity
            </h3>
            <div className="space-y-3">
              {auditLogs.slice(0, 5).map((log) => (
                <div key={log.id} className="border border-slate-900 bg-slate-950/40 rounded-lg p-3.5 flex items-start justify-between gap-4 text-xs">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white uppercase tracking-wider text-[10px]">
                        {log.action}
                      </span>
                      <StatusBadge status={log.event_type} />
                    </div>
                    <p className="text-slate-400 text-[11px]">
                      {log.details?.reason || log.details?.final_action 
                        ? `Action: ${log.details.final_action || log.details.action} | Status: resolved`
                        : `System event recorded at telemetry plane.`}
                    </p>
                  </div>
                  <span className="text-[10px] text-slate-500 whitespace-nowrap shrink-0 mt-0.5">
                    {new Date(log.created_at).toLocaleTimeString()}
                  </span>
                </div>
              ))}
              {auditLogs.length === 0 && (
                <p className="text-xs text-slate-500 py-2">No recent audit log activities recorded.</p>
              )}
            </div>
          </div>
        </div>

        {/* Right Col (1 col): Decision Overview & Control Parameters */}
        <div className="space-y-8">
          
          {/* Decision Overview Breakdown */}
          <div className="border border-slate-800/80 bg-slate-950/20 rounded-xl p-6 backdrop-blur-sm space-y-5">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Shield className="w-4 h-4 text-purple-400" />
              Shield Decision Breakdown
            </h3>
            
            <div className="grid grid-cols-2 gap-4">
              {[
                { status: 'APPROVE', label: 'APPROVED', count: decisionsBreakdown.APPROVE, color: 'text-emerald-400 border-emerald-900/50 bg-emerald-950/20' },
                { status: 'MODIFY', label: 'MODIFIED', count: decisionsBreakdown.MODIFY, color: 'text-cyan-400 border-cyan-900/50 bg-cyan-950/20' },
                { status: 'ESCALATE', label: 'ESCALATED', count: decisionsBreakdown.ESCALATE, color: 'text-purple-400 border-purple-900/50 bg-purple-950/20' },
                { status: 'REJECT', label: 'REJECTED', count: decisionsBreakdown.REJECT, color: 'text-rose-400 border-rose-900/50 bg-rose-950/20' }
              ].map((item) => (
                <div key={item.status} className={`border rounded-lg p-3 text-center ${item.color}`}>
                  <div className="text-[10px] font-bold tracking-wider uppercase opacity-85 mb-1">{item.label}</div>
                  <div className="text-2xl font-black text-white">{item.count}</div>
                </div>
              ))}
            </div>

            <div className="border-t border-slate-900 pt-4 space-y-3.5 divide-y divide-slate-900 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Total Shield Evaluations</span>
                <span className="font-mono text-slate-200 font-bold">{totalDecisions}</span>
              </div>
              <div className="flex justify-between items-center pt-3">
                <span className="text-slate-400">Human Reviews Required</span>
                <span className="font-mono text-slate-200 font-bold">
                  {decisions.filter(d => d.requires_human_review).length}
                </span>
              </div>
            </div>
          </div>

          {/* Control Parameters */}
          <div className="border border-slate-800/80 bg-slate-950/20 rounded-xl p-6 backdrop-blur-sm space-y-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Settings className="w-4 h-4 text-slate-400" />
              Control Parameters
            </h3>
            <div className="space-y-3 divide-y divide-slate-900 text-xs">
              <div className="flex justify-between items-center pb-2.5">
                <span className="text-slate-400">Auto Block Risk Threshold</span>
                <span className="font-mono text-slate-200 font-semibold">0.90 Score</span>
              </div>
              <div className="flex justify-between items-center pt-3 pb-2.5">
                <span className="text-slate-400">Max Discount Limit Policy</span>
                <span className="font-mono text-slate-200 font-semibold">10% Value</span>
              </div>
              <div className="flex justify-between items-center pt-3 pb-2.5">
                <span className="text-slate-400">Max Dunning Retries Policy</span>
                <span className="font-mono text-slate-200 font-semibold">3 Retries</span>
              </div>
              <div className="flex justify-between items-center pt-3">
                <span className="text-slate-400">Database Engine</span>
                <span className="font-mono text-slate-200 font-semibold">Neon PostgreSQL</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
