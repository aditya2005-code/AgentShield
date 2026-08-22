import React from 'react';
import { Database } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
}

export function EmptyState({ title, description, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center border border-dashed border-slate-800 rounded-xl p-12 text-center bg-slate-900/10 backdrop-blur-sm">
      <div className="p-4 rounded-full bg-slate-900 border border-slate-800 text-slate-500 mb-4">
        {icon || <Database className="w-8 h-8" />}
      </div>
      <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
      <p className="text-sm text-slate-400 max-w-sm leading-relaxed">{description}</p>
    </div>
  );
}
