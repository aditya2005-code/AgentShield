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

  return (
    <div className="space-y-6">
      <PageHeader 
        title="AI Agents Registry" 
        description="View Fraud Detection, Payment Recovery, and Growth Incentives agents online in this control plane."
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
        <DataTableShell headers={['Agent Name', 'Key', 'Type', 'Description', 'Status']}>
          {agents.map((agent) => (
            <tr key={agent.id} className="hover:bg-slate-900/10 transition-colors">
              <td className="px-6 py-4 font-bold text-white whitespace-nowrap">{agent.name}</td>
              <td className="px-6 py-4 font-mono text-xs text-slate-400 whitespace-nowrap">{agent.agent_key}</td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                  {agent.agent_type}
                </span>
              </td>
              <td className="px-6 py-4 text-xs text-slate-400 max-w-sm truncate">{agent.description || 'No description provided.'}</td>
              <td className="px-6 py-4 whitespace-nowrap">
                <StatusBadge status={agent.status} />
              </td>
            </tr>
          ))}
        </DataTableShell>
      )}
    </div>
  );
}
