'use client';

import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { EmptyState } from '@/components/shared/empty-state';
import { DataTableShell } from '@/components/shared/data-table-shell';
import { StatusBadge } from '@/components/shared/status-badge';
import { getAuditLogs } from '@/lib/api/client';
import { AuditLog } from '@/types/api';

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getAuditLogs({ limit: 50 });
      setLogs(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load audit logs.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Control Plane Audit Trail" 
        description="Immutable system audit records tracking AI proposals, policies checks, and action override overrides."
      />

      {isLoading && <LoadingState message="Connecting to audit database..." />}

      {!isLoading && error && (
        <ErrorState 
          message={error} 
          onRetry={fetchLogs} 
          isConnectionError={error.includes('failed') || error.includes('fetch')} 
        />
      )}

      {!isLoading && !error && logs.length === 0 && (
        <EmptyState 
          title="No Logs Recorded" 
          description="There are currently no security audit events recorded in the database." 
        />
      )}

      {!isLoading && !error && logs.length > 0 && (
        <DataTableShell headers={['Log ID', 'Event Type', 'Action Taken', 'Audit Details', 'Logged At']}>
          {logs.map((log) => (
            <tr key={log.id} className="hover:bg-slate-900/10 transition-colors">
              <td className="px-6 py-4 font-mono text-xs text-slate-500 whitespace-nowrap">
                {log.id.slice(0, 8)}...
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <StatusBadge status={log.event_type} />
              </td>
              <td className="px-6 py-4 font-bold text-white whitespace-nowrap">{log.action}</td>
              <td className="px-6 py-4 font-mono text-xxs text-slate-400 max-w-xs truncate">
                {JSON.stringify(log.details)}
              </td>
              <td className="px-6 py-4 text-xs text-slate-400 whitespace-nowrap">
                {new Date(log.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </DataTableShell>
      )}
    </div>
  );
}
