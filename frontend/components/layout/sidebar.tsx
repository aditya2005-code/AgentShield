'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  Shield, LayoutDashboard, Cpu, ArrowLeftRight, 
  FileQuestion, ShieldCheck, Scale, History, Play, Menu, X
} from 'lucide-react';

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/', icon: LayoutDashboard },
  { label: 'Agents', path: '/agents', icon: Cpu },
  { label: 'Transactions', path: '/transactions', icon: ArrowLeftRight },
  { label: 'Proposals', path: '/proposals', icon: FileQuestion },
  { label: 'Decisions', path: '/decisions', icon: ShieldCheck },
  { label: 'Policies', path: '/policies', icon: Scale },
  { label: 'Audit Logs', path: '/audit-logs', icon: History },
  { label: 'Demo Scenarios', path: '/demo', icon: Play },
];

export function Sidebar() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = React.useState(false);

  return (
    <>
      {/* Mobile Header */}
      <header className="md:hidden flex items-center justify-between px-4 py-3 border-b border-slate-900 bg-slate-950/80 sticky top-0 z-40">
        <div className="flex items-center gap-2">
          <Shield className="w-6 h-6 text-cyan-400" />
          <span className="font-bold text-white text-lg tracking-wider">AgentShield</span>
        </div>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="p-1 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
          aria-label="Toggle navigation"
        >
          {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </header>

      {/* Sidebar Overlay for Mobile */}
      {isOpen && (
        <div 
          className="md:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40" 
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar Shell */}
      <aside className={`
        fixed md:sticky top-0 left-0 h-screen w-64 bg-slate-950 border-r border-slate-900 flex flex-col z-50 transition-transform duration-300
        md:translate-x-0 ${isOpen ? 'translate-x-0' : '-translate-x-full md:block'}
      `}>
        {/* Sidebar Brand header */}
        <div className="hidden md:flex items-center gap-2.5 px-6 py-5 border-b border-slate-900">
          <Shield className="w-6.5 h-6.5 text-cyan-500" />
          <span className="font-bold text-white tracking-widest text-lg">AgentShield</span>
        </div>

        {/* Sidebar Nav items */}
        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.path;
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                href={item.path}
                onClick={() => setIsOpen(false)}
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group
                  ${isActive 
                    ? 'bg-slate-900 border border-slate-800 text-white font-semibold shadow-inner' 
                    : 'text-slate-400 hover:bg-slate-900/40 hover:text-slate-100 hover:border hover:border-slate-900/55'
                  }
                `}
              >
                <Icon className={`w-4.5 h-4.5 transition-colors ${isActive ? 'text-cyan-400' : 'text-slate-500 group-hover:text-slate-400'}`} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Sidebar Status Footer */}
        <div className="p-4 border-t border-slate-900 bg-slate-900/10 space-y-3">
          <div className="text-xxs font-bold text-slate-500 uppercase tracking-widest px-2">
            Active Guardrails
          </div>
          <div className="space-y-1.5 px-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Fraud Agent
              </span>
              <span className="text-[10px] px-1 bg-emerald-950/20 text-emerald-400 rounded">OK</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Recovery Agent
              </span>
              <span className="text-[10px] px-1 bg-emerald-950/20 text-emerald-400 rounded">OK</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Growth Agent
              </span>
              <span className="text-[10px] px-1 bg-emerald-950/20 text-emerald-400 rounded">OK</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
