'use client';

import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { EmptyState } from '@/components/shared/empty-state';
import { DataTableShell } from '@/components/shared/data-table-shell';
import { getMerchants, getMerchantPolicies } from '@/lib/api/client';
import { Merchant, MerchantPolicy } from '@/types/api';

export default function PoliciesPage() {
  const [merchants, setMerchants] = useState<Merchant[]>([]);
  const [selectedMerchantId, setSelectedMerchantId] = useState<string>('');
  const [policies, setPolicies] = useState<MerchantPolicy[]>([]);
  const [isLoadingMerchants, setIsLoadingMerchants] = useState(true);
  const [isLoadingPolicies, setIsLoadingPolicies] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 1. Fetch all merchants
  const fetchMerchantsData = async () => {
    setIsLoadingMerchants(true);
    setError(null);
    try {
      const data = await getMerchants();
      setMerchants(data);
      if (data.length > 0) {
        // Default to first merchant (which will be VeloCart Electronics)
        setSelectedMerchantId(data[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load merchants list.');
    } finally {
      setIsLoadingMerchants(false);
    }
  };

  // 2. Fetch policies when merchant changes
  const fetchPoliciesData = async (merchantId: string) => {
    if (!merchantId) return;
    setIsLoadingPolicies(true);
    setError(null);
    try {
      const data = await getMerchantPolicies(merchantId);
      setPolicies(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load merchant policies.');
    } finally {
      setIsLoadingPolicies(false);
    }
  };

  useEffect(() => {
    fetchMerchantsData();
  }, []);

  useEffect(() => {
    if (selectedMerchantId) {
      fetchPoliciesData(selectedMerchantId);
    }
  }, [selectedMerchantId]);

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Merchant Risk Policies" 
        description="Verify policies and decision parameters used by AgentShield for authorization checks."
        action={
          merchants.length > 0 && (
            <div className="flex items-center gap-2">
              <label htmlFor="merchant-select" className="text-xs text-slate-400 font-bold uppercase select-none">
                Merchant:
              </label>
              <select
                id="merchant-select"
                value={selectedMerchantId}
                onChange={(e) => setSelectedMerchantId(e.target.value)}
                className="bg-slate-900 border border-slate-800 text-white text-xs font-semibold rounded-lg px-3 py-2 cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-600"
              >
                {merchants.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>
          )
        }
      />

      {(isLoadingMerchants || isLoadingPolicies) && (
        <LoadingState message="Querying merchant guardrail policies..." />
      )}

      {!(isLoadingMerchants || isLoadingPolicies) && error && (
        <ErrorState 
          message={error} 
          onRetry={fetchMerchantsData} 
          isConnectionError={error.includes('failed') || error.includes('fetch')} 
        />
      )}

      {!(isLoadingMerchants || isLoadingPolicies) && !error && policies.length === 0 && (
        <EmptyState 
          title="No Active Policies" 
          description="There are currently no risk policies configured for the selected merchant." 
        />
      )}

      {!(isLoadingMerchants || isLoadingPolicies) && !error && policies.length > 0 && (
        <DataTableShell headers={['Policy Key', 'Name', 'Configured Value', 'Status']}>
          {policies.map((policy) => (
            <tr key={policy.id} className="hover:bg-slate-900/10 transition-colors">
              <td className="px-6 py-4 font-mono text-xs text-cyan-400 whitespace-nowrap">{policy.policy_key}</td>
              <td className="px-6 py-4 font-bold text-white whitespace-nowrap">{policy.policy_name}</td>
              <td className="px-6 py-4 font-mono text-xs text-slate-300 whitespace-nowrap">
                {JSON.stringify(policy.policy_value)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold tracking-wide border uppercase ${
                  policy.is_active 
                    ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800/50' 
                    : 'bg-slate-800 text-slate-400 border-slate-700/60'
                }`}>
                  {policy.is_active ? 'ACTIVE' : 'INACTIVE'}
                </span>
              </td>
            </tr>
          ))}
        </DataTableShell>
      )}
    </div>
  );
}
