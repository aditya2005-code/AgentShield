import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  rows?: number;
}

export function LoadingState({ message = "Loading database contents...", rows = 3 }: LoadingStateProps) {
  return (
    <div className="space-y-6 w-full">
      {/* Centered spinner / indicator */}
      <div className="flex items-center justify-center py-6 gap-3 text-slate-400">
        <Loader2 className="w-5 h-5 animate-spin text-cyan-500" />
        <span className="text-sm font-medium">{message}</span>
      </div>

      {/* Grid of skeleton rows */}
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="w-full h-12 bg-slate-900/40 border border-slate-800/80 rounded-lg animate-pulse flex items-center justify-between px-4">
            <div className="flex items-center gap-3 w-1/3">
              <div className="w-8 h-8 rounded bg-slate-800" />
              <div className="h-4 bg-slate-800 rounded w-full" />
            </div>
            <div className="h-4 bg-slate-800 rounded w-1/6" />
            <div className="h-4 bg-slate-800 rounded w-1/12" />
          </div>
        ))}
      </div>
    </div>
  );
}
