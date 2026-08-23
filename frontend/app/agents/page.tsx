'use client';

import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { EmptyState } from '@/components/shared/empty-state';
import { DataTableShell } from '@/components/shared/data-table-shell';
import { StatusBadge } from '@/components/shared/status-badge';
import { getAgents } from '@/lib/api/client';
import { Agent } from '@/types/api';
import { Shield, Coins, Sparkles, Key } from 'lucide-react';

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAgents = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getAgents();
      setAgents(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load agents.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const getAgentTheme = (type: string) => {
    switch (type.toUpperCase()) {
      case 'FRAUD':
        return {
          icon: <Shield className="w-5 h-5 text-rose-400" />,
          bgColor: 'bg-rose-950/15',
          borderColor: 'border-rose-900/40',
          badgeStyle: 'bg-rose-950/40 text-rose-400 border-rose-800/40',
          accentColor: 'bg-rose-500',
          textColor: 'text-rose-400'
        };
      case 'RECOVERY':
        return {
          icon: <Coins className="w-5 h-5 text-blue-400" />,
          bgColor: 'bg-blue-950/15',
          borderColor: 'border-blue-900/40',
          badgeStyle: 'bg-blue-950/40 text-blue-400 border-blue-800/40',
          accentColor: 'bg-blue-500',
          textColor: 'text-blue-400'
        };
      case 'GROWTH':
        return {
          icon: <Sparkles className="w-5 h-5 text-emerald-400" />,
          bgColor: 'bg-emerald-950/15',
          borderColor: 'border-emerald-900/40',
          badgeStyle: 'bg-emerald-950/40 text-emerald-400 border-emerald-800/40',
          accentColor: 'bg-emerald-500',
          textColor: 'text-emerald-400'
        };
      default:
        return {
          icon: <Shield className="w-5 h-5 text-slate-400" />,
          bgColor: 'bg-slate-900/20',
          borderColor: 'border-slate-800',
          badgeStyle: 'bg-slate-800 text-slate-300 border-slate-700',
          accentColor: 'bg-slate-500',
          textColor: 'text-slate-400'
        };
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader 
        title="AI Agents Registry" 
        description="View and verify the operational status of deployed security, recovery, and growth decision agents."
      />

      {isLoading && <LoadingState message="Connecting to agent database..." />}

      {!isLoading && error && (
        <ErrorState 
          message={error} 
          onRetry={fetchAgents} 
          isConnectionError={error.includes('failed') || error.includes('fetch')} 
        />
      )}

      {!isLoading && !error && agents.length === 0 && (
        <EmptyState 
          title="No Agents Registered" 
          description="There are currently no AI agents registered in the database." 
        />
      )}

      {!isLoading && !error && agents.length > 0 && (
        <div className="space-y-8">
          
          {/* Agent Visual Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {agents.map((agent) => {
              const theme = getAgentTheme(agent.agent_type);
              return (
                <div 
                  key={agent.id} 
                  className={`border ${theme.borderColor} ${theme.bgColor} rounded-xl p-5 relative overflow-hidden flex flex-col justify-between group`}
                >
                  <div className={`absolute top-0 left-0 w-full h-[2px] ${theme.accentColor}`} />
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <div className="p-2 rounded bg-slate-950 border border-slate-900">
                        {theme.icon}
                      </div>
                      <span className={`text-xs font-bold px-2 py-0.5 border rounded uppercase ${theme.badgeStyle}`}>
                        {agent.agent_type}
                      </span>
                    </div>
                    
                    <div>
                      <h3 className="font-bold text-white text-base leading-tight mb-1">
                        {agent.name}
                      </h3>
                      <p className="text-slate-400 text-xs leading-relaxed">
                        {agent.description || 'No description provided for this specialized agent.'}
                      </p>
                    </div>
                  </div>

                  <div className="mt-5 pt-3 border-t border-slate-900 flex justify-between items-center text-[10px] text-slate-500 font-mono">
                    <span className="flex items-center gap-1">
                      <Key className="w-3.5 h-3.5" />
                      {agent.agent_key}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${agent.status === 'ACTIVE' ? 'bg-emerald-500' : 'bg-slate-600'}`} />
                      {agent.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Database Details Table */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Registry Raw Telemetry</h3>
            <DataTableShell headers={['Agent Name', 'Key', 'Type', 'Description', 'Status']}>
              {agents.map((agent) => {
                const theme = getAgentTheme(agent.agent_type);
                return (
                  <tr key={agent.id} className="hover:bg-slate-900/10 transition-colors">
                    <td className="px-6 py-4 font-bold text-white whitespace-nowrap">{agent.name}</td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-400 whitespace-nowrap">{agent.agent_key}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded border uppercase ${theme.badgeStyle}`}>
                        {agent.agent_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-400 max-w-sm truncate">{agent.description || 'No description provided.'}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={agent.status} />
                    </td>
                  </tr>
                );
              })}
            </DataTableShell>
          </div>
        </div>
      )}
    </div>
  );
}
