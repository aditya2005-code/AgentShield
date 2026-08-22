'use client';

import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { EmptyState } from '@/components/shared/empty-state';
import { DataTableShell } from '@/components/shared/data-table-shell';
import { StatusBadge } from '@/components/shared/status-badge';
import { getProposals } from '@/lib/api/client';
import { ActionProposal } from '@/types/api';

export default function ProposalsPage() {
  const [proposals, setProposals] = useState<ActionProposal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProposals = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getProposals();
      setProposals(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load proposals.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProposals();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Agent Action Proposals" 
        description="Verify and audit operational actions proposed by Fraud, Recovery, and Growth AI agents."
      />

      {isLoading && <LoadingState message="Connecting to proposals database..." />}

      {!isLoading && error && (
        <ErrorState 
          message={error} 
          onRetry={fetchProposals} 
          isConnectionError={error.includes('failed') || error.includes('fetch')} 
        />
      )}

      {!isLoading && !error && proposals.length === 0 && (
        <EmptyState 
          title="No Proposals Found" 
          description="There are currently no action proposals recorded in the database." 
        />
      )}

      {!isLoading && !error && proposals.length > 0 && (
        <DataTableShell headers={['Proposal ID', 'Event Type', 'Proposed Action', 'Confidence', 'Fin. Impact', 'Cust. Impact', 'Status', 'Proposed At']}>
          {proposals.map((prop) => (
            <tr key={prop.proposal_id} className="hover:bg-slate-900/10 transition-colors">
              <td className="px-6 py-4 font-mono text-xs text-cyan-400 whitespace-nowrap">
                {prop.proposal_id.slice(0, 8)}...
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                  {prop.event_type}
                </span>
              </td>
              <td className="px-6 py-4 font-bold text-white whitespace-nowrap">{prop.action}</td>
              <td className="px-6 py-4 font-mono text-xs text-slate-300 whitespace-nowrap">
                {(Number(prop.confidence) * 100).toFixed(0)}%
              </td>
              <td className="px-6 py-4 text-xs font-semibold text-slate-300 whitespace-nowrap">{prop.financial_impact}</td>
              <td className="px-6 py-4 text-xs font-semibold text-slate-300 whitespace-nowrap">{prop.customer_impact}</td>
              <td className="px-6 py-4 whitespace-nowrap">
                <StatusBadge status={prop.status} />
              </td>
              <td className="px-6 py-4 text-xs text-slate-400 whitespace-nowrap">
                {new Date(prop.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </DataTableShell>
      )}
    </div>
  );
}
