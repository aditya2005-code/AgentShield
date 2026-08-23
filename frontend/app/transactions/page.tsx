'use client';

import React, { useEffect, useState } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingState } from '@/components/shared/loading-state';
import { ErrorState } from '@/components/shared/error-state';
import { EmptyState } from '@/components/shared/empty-state';
import { DataTableShell } from '@/components/shared/data-table-shell';
import { StatusBadge } from '@/components/shared/status-badge';
import { DetailDrawer } from '@/components/shared/detail-drawer';
import { getTransactions, getTransactionById, getMerchants } from '@/lib/api/client';
import { Transaction, TransactionDetail, Merchant } from '@/types/api';
import { 
  Building, 
  User, 
  Laptop, 
  Globe, 
  CreditCard, 
  Calendar, 
  ChevronLeft, 
  ChevronRight, 
  Eye 
} from 'lucide-react';

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [merchants, setMerchants] = useState<Merchant[]>([]);
  const [selectedTx, setSelectedTx] = useState<TransactionDetail | null>(null);
  
  // Filtering & Pagination State
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [merchantFilter, setMerchantFilter] = useState<string>('');
  const [limit] = useState<number>(20);
  const [offset, setOffset] = useState<number>(0);
  
  // Loading & Error states
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const loadFilterOptions = async () => {
    try {
      const data = await getMerchants();
      setMerchants(data);
    } catch (err) {
      console.error('Failed to pre-fetch merchants for filters:', err);
    }
  };

  const fetchTransactionsData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getTransactions({
        limit,
        offset,
        status: statusFilter || undefined,
        merchant_id: merchantFilter || undefined
      });
      setTransactions(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load transactions list.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadFilterOptions();
  }, []);

  useEffect(() => {
    fetchTransactionsData();
  }, [statusFilter, merchantFilter, offset]);

  // Handle pagination clicks
  const handlePrevPage = () => {
    if (offset >= limit) {
      setOffset(offset - limit);
    }
  };

  const handleNextPage = () => {
    if (transactions.length === limit) {
      setOffset(offset + limit);
    }
  };

  // Open detail panel
  const handleViewDetail = async (txId: string) => {
    setIsLoadingDetail(true);
    setDetailError(null);
    setSelectedTx(null);
    setIsDrawerOpen(true);
    try {
      const detail = await getTransactionById(txId);
      setSelectedTx(detail);
    } catch (err: any) {
      setDetailError(err.message || 'Failed to query transaction details from the server.');
    } finally {
      setIsLoadingDetail(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Transaction Stream" 
        description="Monitor real-time merchant transaction telemetry feeding into operational risk models."
        action={
          <div className="flex flex-wrap items-center gap-3">
            {/* Merchant selector */}
            <div className="flex items-center gap-1.5">
              <label htmlFor="merchant-select" className="text-[10px] text-slate-500 font-bold uppercase select-none">
                Merchant
              </label>
              <select
                id="merchant-select"
                value={merchantFilter}
                onChange={(e) => { setMerchantFilter(e.target.value); setOffset(0); }}
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

            {/* Status selector */}
            <div className="flex items-center gap-1.5">
              <label htmlFor="status-select" className="text-[10px] text-slate-500 font-bold uppercase select-none">
                Status
              </label>
              <select
                id="status-select"
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setOffset(0); }}
                className="bg-slate-900 border border-slate-800 text-white text-xs font-semibold rounded-lg px-2.5 py-1.5 cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-600"
              >
                <option value="">ALL STATUSES</option>
                <option value="PENDING">PENDING</option>
                <option value="SUCCESS">SUCCESS</option>
                <option value="FAILED">FAILED</option>
                <option value="BLOCKED">BLOCKED</option>
              </select>
            </div>
          </div>
        }
      />

      {isLoading && <LoadingState message="Connecting to transaction database..." />}

      {!isLoading && error && (
        <ErrorState 
          message={error} 
          onRetry={fetchTransactionsData} 
          isConnectionError={error.includes('failed') || error.includes('fetch')} 
        />
      )}

      {!isLoading && !error && transactions.length === 0 && (
        <EmptyState 
          title="No Transactions Found" 
          description="There are currently no transactions matching the selected filters recorded in the database." 
        />
      )}

      {!isLoading && !error && transactions.length > 0 && (
        <div className="space-y-4">
          <DataTableShell headers={['Tx ID', 'Amount', 'Currency', 'Payment Method', 'Location', 'Status', 'Occurred At', 'Actions']}>
            {transactions.map((tx) => (
              <tr 
                key={tx.id} 
                onClick={() => handleViewDetail(tx.id)}
                className="hover:bg-slate-900/10 cursor-pointer transition-colors"
              >
                <td className="px-6 py-4 font-mono text-xs text-cyan-400 whitespace-nowrap">
                  {tx.external_transaction_id}
                </td>
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
                <td className="px-6 py-4 text-right whitespace-nowrap">
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleViewDetail(tx.id); }}
                    className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
                    aria-label={`View details of transaction ${tx.external_transaction_id}`}
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </DataTableShell>

          {/* Pagination controls */}
          <div className="flex justify-between items-center bg-slate-950/20 border border-slate-900 rounded-xl px-6 py-4">
            <span className="text-xs text-slate-400">
              Showing records <span className="font-mono font-bold text-white">{offset + 1}</span> to{' '}
              <span className="font-mono font-bold text-white">{offset + transactions.length}</span>
            </span>

            <div className="flex gap-2">
              <button
                disabled={offset === 0}
                onClick={handlePrevPage}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-800 bg-slate-900 text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-all"
              >
                <ChevronLeft className="w-3.5 h-3.5" /> Previous
              </button>
              <button
                disabled={transactions.length < limit}
                onClick={handleNextPage}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-800 bg-slate-900 text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-all"
              >
                Next <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Transaction Details Slide-over Drawer */}
      <DetailDrawer 
        isOpen={isDrawerOpen} 
        onClose={() => setIsDrawerOpen(false)}
        title={selectedTx ? `Transaction details: ${selectedTx.external_transaction_id}` : 'Querying Transaction details'}
      >
        {isLoadingDetail && (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mb-3" />
            <span className="text-xs">Fetching nested customer and device records...</span>
          </div>
        )}

        {detailError && (
          <div className="p-4 bg-rose-950/10 border border-rose-900/30 text-rose-400 text-xs rounded-lg">
            {detailError}
          </div>
        )}

        {!isLoadingDetail && !detailError && selectedTx && (
          <div className="space-y-6">
            
            {/* Core Transaction Card */}
            <div className="border border-slate-800 bg-slate-900/10 rounded-xl p-5 space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Transaction Value</span>
                  <div className="text-2xl font-black text-white mt-1">
                    {selectedTx.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}{' '}
                    <span className="text-sm font-normal text-slate-400">{selectedTx.currency}</span>
                  </div>
                </div>
                <StatusBadge status={selectedTx.status} />
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs pt-2">
                <div className="flex items-center gap-2 border-b border-slate-900 pb-2">
                  <CreditCard className="w-4 h-4 text-slate-500" />
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase">Payment Method</div>
                    <div className="text-white font-medium">{selectedTx.payment_method}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2 border-b border-slate-900 pb-2">
                  <Globe className="w-4 h-4 text-slate-500" />
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase">IP Location</div>
                    <div className="text-white font-medium">{selectedTx.location}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2 pt-1 col-span-2">
                  <Calendar className="w-4 h-4 text-slate-500" />
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase">Occurred At</div>
                    <div className="text-white font-medium">{new Date(selectedTx.occurred_at).toLocaleString()}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Merchant Details Block */}
            <div className="border border-slate-900 bg-slate-950/40 rounded-xl p-4 space-y-3">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                <Building className="w-3.5 h-3.5 text-cyan-400" />
                Merchant Context
              </h4>
              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Merchant Name</span>
                  <span className="text-white font-bold">{selectedTx.merchant.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Slug Identifier</span>
                  <span className="font-mono text-slate-300">{selectedTx.merchant.slug}</span>
                </div>
              </div>
            </div>

            {/* Customer Details Block */}
            <div className="border border-slate-900 bg-slate-950/40 rounded-xl p-4 space-y-3">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-cyan-400" />
                Customer Identity
              </h4>
              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Customer Name</span>
                  <span className="text-white font-bold">{selectedTx.customer.full_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Email Address</span>
                  <span className="text-slate-300">{selectedTx.customer.email}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">External ID</span>
                  <span className="font-mono text-slate-400">{selectedTx.customer.external_customer_id}</span>
                </div>
              </div>
            </div>

            {/* Device Details Block */}
            <div className="border border-slate-900 bg-slate-950/40 rounded-xl p-4 space-y-3">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                <Laptop className="w-3.5 h-3.5 text-cyan-400" />
                Device Fingerprint
              </h4>
              {selectedTx.device ? (
                <div className="space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Device Type</span>
                    <span className="text-white font-semibold">{selectedTx.device.device_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Fingerprint SHA</span>
                    <span className="font-mono text-[10px] text-slate-400">{selectedTx.device.device_fingerprint}</span>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-slate-500 italic">No device fingerprint was captured for this transaction.</div>
              )}
            </div>
            
          </div>
        )}
      </DetailDrawer>
    </div>
  );
}
