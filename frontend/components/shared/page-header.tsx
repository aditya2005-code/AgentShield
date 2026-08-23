import React from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="flex flex-col md:flex-row md:items-center md:justify-between border-b border-slate-900 pb-5 mb-6 gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">{title}</h1>
        {description && (
          <p className="text-sm text-slate-400 mt-1 leading-relaxed">{description}</p>
        )}
      </div>
      {action && <div className="flex items-center gap-3">{action}</div>}
    </div>
  );
}
