'use client';

import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { EmptyState } from '@/components/shared/empty-state';
import { DataTableShell } from '@/components/shared/data-table-shell';
import { StatusBadge } from '@/components/shared/status-badge';
import { getTransactions } from '@/lib/api/client';
import { Transaction } from '@/types/api';

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTransactions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Fetch newest 50 transactions
      const data = await getTransactions({ limit: 50 });
      setTransactions(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load transactions.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Transaction Stream" 
        description="Monitor real-time merchant transaction data feeding into Fraud scoring agents."
      />

      {isLoading && <LoadingState message="Connecting to transaction database..." />}

      {!isLoading && error && (
        <ErrorState 
          message={error} 
          onRetry={fetchTransactions} 
          isConnectionError={error.includes('failed') || error.includes('fetch')} 
        />
      )}

      {!isLoading && !error && transactions.length === 0 && (
        <EmptyState 
          title="No Transactions Found" 
          description="There are currently no transactions recorded in the database." 
        />
      )}

      {!isLoading && !error && transactions.length > 0 && (
        <DataTableShell headers={['Tx ID', 'Amount', 'Currency', 'Payment Method', 'Location', 'Status', 'Occurred At']}>
          {transactions.map((tx) => (
            <tr key={tx.id} className="hover:bg-slate-900/10 transition-colors">
              <td className="px-6 py-4 font-mono text-xs text-cyan-400 whitespace-nowrap">{tx.external_transaction_id}</td>
              <td className="px-6 py-4 font-bold text-white whitespace-nowrap">
                {tx.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </td>
              <td className="px-6 py-4 text-xs font-semibold uppercase text-slate-400 whitespace-nowrap">{tx.currency}</td>
              <td className="px-6 py-4 text-xs text-slate-300 whitespace-nowrap">{tx.payment_method}</td>
              <td className="px-6 py-4 text-xs text-slate-300 whitespace-nowrap">{tx.location}</td>
              <td className="px-6 py-4 whitespace-nowrap">
                <StatusBadge status={tx.status} />
              </td>
              <td className="px-6 py-4 text-xs text-slate-400 whitespace-nowrap">
                {new Date(tx.occurred_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </DataTableShell>
      )}
    </div>
  );
}
