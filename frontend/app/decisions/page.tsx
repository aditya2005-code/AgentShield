'use client';

import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { EmptyState } from '@/components/shared/empty-state';
import { DataTableShell } from '@/components/shared/data-table-shell';
import { StatusBadge } from '@/components/shared/status-badge';
import { getDecisions } from '@/lib/api/client';
import { ShieldDecision } from '@/types/api';

export default function DecisionsPage() {
  const [decisions, setDecisions] = useState<ShieldDecision[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDecisions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getDecisions();
      setDecisions(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load decisions.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDecisions();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader 
        title="AgentShield Decisions Log" 
        description="Audit policy evaluations and action overrides executed by the AgentShield control plane."
      />

      {isLoading && <LoadingState message="Connecting to decisions database..." />}

      {!isLoading && error && (
        <ErrorState 
          message={error} 
          onRetry={fetchDecisions} 
          isConnectionError={error.includes('failed') || error.includes('fetch')} 
        />
      )}

      {!isLoading && !error && decisions.length === 0 && (
        <EmptyState 
          title="No Decisions Recorded" 
          description="There are currently no AgentShield decisions recorded in the database." 
        />
      )}

      {!isLoading && !error && decisions.length > 0 && (
        <DataTableShell headers={['Decision ID', 'Decision', 'Final Action', 'Checks Count', 'Human Review', 'Decided At']}>
          {decisions.map((dec) => (
            <tr key={dec.decision_id} className="hover:bg-slate-900/10 transition-colors">
              <td className="px-6 py-4 font-mono text-xs text-cyan-400 whitespace-nowrap">
                {dec.decision_id.slice(0, 8)}...
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <StatusBadge status={dec.decision} />
              </td>
              <td className="px-6 py-4 font-bold text-white whitespace-nowrap">{dec.final_action}</td>
              <td className="px-6 py-4 text-xs text-slate-300 whitespace-nowrap">
                {dec.checks.length} Check(s)
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${
                  dec.requires_human_review 
                    ? 'bg-amber-950/20 text-amber-400 border-amber-800/40' 
                    : 'bg-slate-800 text-slate-400 border-slate-700/60'
                }`}>
                  {dec.requires_human_review ? 'REQUIRED' : 'AUTO_RESOLVED'}
                </span>
              </td>
              <td className="px-6 py-4 text-xs text-slate-400 whitespace-nowrap">
                {new Date(dec.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </DataTableShell>
      )}
    </div>
  );
}
