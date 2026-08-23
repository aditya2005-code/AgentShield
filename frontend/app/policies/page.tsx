'use client';

import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { EmptyState } from '@/components/shared/empty-state';
import { DataTableShell } from '@/components/shared/data-table-shell';
import { getMerchants, getMerchantPolicies } from '@/lib/api/client';
import { Merchant, MerchantPolicy } from '@/types/api';
import { ShieldAlert, BookOpen, ToggleLeft, Settings } from 'lucide-react';

export default function PoliciesPage() {
  const [merchants, setMerchants] = useState<Merchant[]>([]);
  const [selectedMerchantId, setSelectedMerchantId] = useState<string>('');
  const [policies, setPolicies] = useState<MerchantPolicy[]>([]);
  
  // States
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
        // Default to first merchant (velocart-electronics)
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

  // Visual helper to parse policy JSON config and display readable values
  const formatPolicyValue = (key: string, value: Record<string, any>) => {
    if (!value) return 'N/A';
    
    // Check if the value follows a standard {"value": X} wrapper
    const innerValue = value.value !== undefined ? value.value : value;

    switch (key.toLowerCase()) {
      case 'max_discount_percent':
        return `${innerValue}% Limit`;
      case 'max_recovery_retries':
        return `${innerValue} Retries`;
      case 'high_value_threshold':
        return `INR ${Number(innerValue).toLocaleString()}`;
      case 'auto_block_threshold':
        return `${innerValue} Risk Score`;
      default:
        // Render JSON keys nicely if it is an object
        if (typeof innerValue === 'object') {
          return Object.entries(innerValue)
            .map(([k, v]) => `${k}: ${v}`)
            .join(', ');
        }
        return String(innerValue);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Merchant Guardrail Policies" 
        description="Verify security rule settings and decision boundaries evaluated by AgentShield checks."
        action={
          merchants.length > 0 && (
            <div className="flex items-center gap-2">
              <label htmlFor="merchant-select" className="text-xs text-slate-400 font-bold uppercase select-none">
                Merchant Profile:
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
          title="No Configured Policies" 
          description="There are currently no risk policies configured for the selected merchant in the database." 
        />
      )}

      {!(isLoadingMerchants || isLoadingPolicies) && !error && policies.length > 0 && (
        <div className="space-y-6">
          
          {/* Card Overview Summary */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {policies.map((policy) => (
              <div key={policy.id} className="border border-slate-850 bg-slate-950/20 rounded-xl p-4 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-center text-[10px] text-slate-500 font-bold uppercase mb-2">
                    <span className="font-mono text-cyan-400">{policy.policy_key}</span>
                    <span className={`w-1.5 h-1.5 rounded-full ${policy.is_active ? 'bg-emerald-500' : 'bg-slate-600'}`} />
                  </div>
                  <h4 className="font-bold text-white text-xs leading-snug">{policy.policy_name}</h4>
                  <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                    {policy.description || 'Merchant-enforced boundary override rule.'}
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-900 flex justify-between items-center">
                  <span className="text-[10px] text-slate-500 font-mono">Bound:</span>
                  <span className="text-xs font-mono text-emerald-400 font-bold">
                    {formatPolicyValue(policy.policy_key, policy.policy_value)}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Details Table */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Active System Parameters</h3>
            <DataTableShell headers={['Policy Key', 'Name', 'Configured Value', 'Description', 'Active Status']}>
              {policies.map((policy) => (
                <tr key={policy.id} className="hover:bg-slate-900/10 transition-colors text-xs">
                  <td className="px-6 py-4 font-mono text-cyan-400 whitespace-nowrap">{policy.policy_key}</td>
                  <td className="px-6 py-4 font-bold text-white whitespace-nowrap">{policy.policy_name}</td>
                  <td className="px-6 py-4 font-mono text-emerald-400 font-bold whitespace-nowrap">
                    {formatPolicyValue(policy.policy_key, policy.policy_value)}
                  </td>
                  <td className="px-6 py-4 text-slate-400 max-w-xs truncate">{policy.description || 'System guardrail check.'}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${
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
          </div>
        </div>
      )}
    </div>
  );
}
