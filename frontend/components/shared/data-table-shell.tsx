import React from 'react';

interface DataTableShellProps {
  headers: string[];
  children: React.ReactNode;
}

export function DataTableShell({ headers, children }: DataTableShellProps) {
  return (
    <div className="w-full overflow-hidden border border-slate-800/80 rounded-xl bg-slate-950/40 backdrop-blur-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-sm text-slate-300">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-900/30 text-slate-400 font-semibold tracking-wider text-xs uppercase">
              {headers.map((h, i) => (
                <th key={i} className="px-6 py-3.5 whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/40">
            {children}
          </tbody>
        </table>
      </div>
    </div>
  );
}
