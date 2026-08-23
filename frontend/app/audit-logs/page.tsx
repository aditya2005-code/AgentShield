'use client';

import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { EmptyState } from '@/components/shared/empty-state';
import { DataTableShell } from '@/components/shared/data-table-shell';
import { StatusBadge } from '@/components/shared/status-badge';
import { DetailDrawer } from '@/components/shared/detail-drawer';
import { getAuditLogs, getAgents, getMerchants } from '@/lib/api/client';
import { AuditLog, Agent, Merchant } from '@/types/api';
import { Sliders, Calendar, Cpu, Building, FileText, Shield, Eye } from 'lucide-react';

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [merchants, setMerchants] = useState<Merchant[]>([]);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  // Filters State
  const [agentFilter, setAgentFilter] = useState<string>('');
  const [merchantFilter, setMerchantFilter] = useState<string>('');
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('');

  // Page States
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
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
      console.error('Failed to load audit filters:', err);
    }
  };

  const fetchLogsData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getAuditLogs({
        agent_id: agentFilter || undefined,
        merchant_id: merchantFilter || undefined,
        event_type: eventTypeFilter || undefined,
        limit: 50
      });
      setLogs(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load audit logs.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFilters();
  }, []);

  useEffect(() => {
    fetchLogsData();
  }, [agentFilter, merchantFilter, eventTypeFilter]);

  const handleOpenDetail = (log: AuditLog) => {
    setSelectedLog(log);
    setIsDrawerOpen(true);
  };

  // Helper to format JSON payload neatly
  const formatJSONDetails = (details: Record<string, any>) => {
    if (!details || Object.keys(details).length === 0) {
      return <div className="text-slate-500 italic">No additional metadata logged.</div>;
    }
    return (
      <pre className="text-[11px] font-mono p-4 bg-slate-950 border border-slate-900 rounded-lg text-emerald-400 overflow-x-auto whitespace-pre-wrap leading-relaxed max-w-full">
        {JSON.stringify(details, null, 2)}
      </pre>
    );
  };

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Control Plane Audit Trail" 
        description="Immutable system audit records tracking AI proposals, policies checks, and action overrides."
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

            {/* Event Type Select */}
            <div className="flex items-center gap-1.5">
              <label htmlFor="event-type-select" className="text-[10px] text-slate-500 font-bold uppercase select-none">
                Event Type
              </label>
              <select
                id="event-type-select"
                value={eventTypeFilter}
                onChange={(e) => setEventTypeFilter(e.target.value)}
                className="bg-slate-900 border border-slate-800 text-white text-xs font-semibold rounded-lg px-2.5 py-1.5 cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-600"
              >
                <option value="">ALL EVENTS</option>
                <option value="AGENT_PROPOSAL_CREATED">PROPOSAL CREATED</option>
                <option value="SHIELD_DECISION_CREATED">SHIELD DECISION</option>
                <option value="ACTION_EXECUTED">ACTION EXECUTED</option>
              </select>
            </div>
          </div>
        }
      />

      {isLoading && <LoadingState message="Connecting to audit database..." />}

      {!isLoading && error && (
        <ErrorState 
          message={error} 
          onRetry={fetchLogsData} 
          isConnectionError={error.includes('failed') || error.includes('fetch')} 
        />
      )}

      {!isLoading && !error && logs.length === 0 && (
        <EmptyState 
          title="No Logs Recorded" 
          description="There are currently no security audit events matching the selected filters recorded in the database." 
        />
      )}

      {!isLoading && !error && logs.length > 0 && (
        <DataTableShell headers={['Log ID', 'Event Type', 'Action Taken', 'Related Entities', 'Logged At', 'Actions']}>
          {logs.map((log) => {
            // Find corresponding agent/merchant summaries
            const agentObj = agents.find(a => a.id === log.agent_id);
            const merchantObj = merchants.find(m => m.id === log.merchant_id);

            return (
              <tr 
                key={log.id} 
                onClick={() => handleOpenDetail(log)}
                className="hover:bg-slate-900/10 cursor-pointer transition-colors text-xs"
              >
                <td className="px-6 py-4 font-mono text-slate-500 whitespace-nowrap">
                  {log.id.slice(0, 8)}...
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <StatusBadge status={log.event_type} />
                </td>
                <td className="px-6 py-4 font-bold text-white whitespace-nowrap">{log.action}</td>
                <td className="px-6 py-4 text-slate-400 whitespace-nowrap">
                  <div className="flex flex-col gap-0.5">
                    {agentObj && (
                      <span className="text-[10px] text-slate-400 flex items-center gap-1">
                        <Cpu className="w-3 h-3 text-cyan-500" /> {agentObj.name}
                      </span>
                    )}
                    {merchantObj && (
                      <span className="text-[10px] text-slate-400 flex items-center gap-1">
                        <Building className="w-3 h-3 text-indigo-500" /> {merchantObj.name}
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 text-slate-400 whitespace-nowrap">
                  {new Date(log.created_at).toLocaleString()}
                </td>
                <td className="px-6 py-4 text-right whitespace-nowrap">
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleOpenDetail(log); }}
                    className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
                    aria-label={`View details of audit log ${log.id}`}
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            );
          })}
        </DataTableShell>
      )}

      {/* Audit Log Detail Drawer */}
      <DetailDrawer 
        isOpen={isDrawerOpen} 
        onClose={() => setIsDrawerOpen(false)}
        title={selectedLog ? `Audit log detail: ${selectedLog.id.slice(0, 8)}...` : 'Audit Log Detail'}
      >
        {selectedLog && (
          <div className="space-y-6">
            
            {/* Core Info */}
            <div className="border border-slate-800 bg-slate-900/10 rounded-xl p-5 space-y-4">
              <div>
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Audit Event</span>
                <div className="flex items-center gap-2 mt-1">
                  <StatusBadge status={selectedLog.event_type} />
                  <h3 className="font-bold text-white text-sm">{selectedLog.action}</h3>
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs pt-3 border-t border-slate-900 text-slate-400">
                <Calendar className="w-4 h-4 text-slate-500" />
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Logged At</div>
                  <div className="text-white font-medium">{new Date(selectedLog.created_at).toLocaleString()}</div>
                </div>
              </div>
            </div>

            {/* Related IDs */}
            <div className="border border-slate-900 bg-slate-950/40 rounded-xl p-4 space-y-3">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Linked Control Plane References</h4>
              <div className="space-y-2 text-xs">
                {selectedLog.agent_id && (
                  <div className="flex justify-between items-center py-1">
                    <span className="text-slate-400 flex items-center gap-1.5"><Cpu className="w-3.5 h-3.5 text-cyan-500" /> Agent UUID</span>
                    <span className="font-mono text-[10px] text-white bg-slate-950 px-2 py-0.5 border border-slate-900 rounded">{selectedLog.agent_id}</span>
                  </div>
                )}
                {selectedLog.merchant_id && (
                  <div className="flex justify-between items-center py-1">
                    <span className="text-slate-400 flex items-center gap-1.5"><Building className="w-3.5 h-3.5 text-indigo-500" /> Merchant UUID</span>
                    <span className="font-mono text-[10px] text-white bg-slate-950 px-2 py-0.5 border border-slate-900 rounded">{selectedLog.merchant_id}</span>
                  </div>
                )}
                {selectedLog.proposal_id && (
                  <div className="flex justify-between items-center py-1">
                    <span className="text-slate-400 flex items-center gap-1.5"><FileText className="w-3.5 h-3.5 text-purple-500" /> Proposal UUID</span>
                    <span className="font-mono text-[10px] text-white bg-slate-950 px-2 py-0.5 border border-slate-900 rounded">{selectedLog.proposal_id}</span>
                  </div>
                )}
                {selectedLog.decision_id && (
                  <div className="flex justify-between items-center py-1">
                    <span className="text-slate-400 flex items-center gap-1.5"><Shield className="w-3.5 h-3.5 text-amber-500" /> Decision UUID</span>
                    <span className="font-mono text-[10px] text-white bg-slate-950 px-2 py-0.5 border border-slate-900 rounded">{selectedLog.decision_id}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Event Payload */}
            <div className="space-y-2">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Logged Data Payload</h4>
              {formatJSONDetails(selectedLog.details)}
            </div>

          </div>
        )}
      </DetailDrawer>
    </div>
  );
}
