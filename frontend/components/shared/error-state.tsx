import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  isConnectionError?: boolean;
}

export function ErrorState({ title = "An error occurred", message, onRetry, isConnectionError = false }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center border border-rose-950/20 bg-rose-950/5 rounded-xl p-8 text-center max-w-lg mx-auto">
      <div className="p-3 rounded-full bg-rose-950/20 border border-rose-800/30 text-rose-400 mb-4">
        <AlertCircle className="w-8 h-8" />
      </div>
      <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
      <p className="text-sm text-slate-400 leading-relaxed mb-6">{message}</p>
      
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg border border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800 hover:text-white transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-slate-600 focus:ring-offset-2 focus:ring-offset-slate-950"
        >
          <RefreshCw className="w-4 h-4" />
          {isConnectionError ? "Retry Connection" : "Try Again"}
        </button>
      )}
    </div>
  );
}
