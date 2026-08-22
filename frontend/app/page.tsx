'use client';

import React from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { Shield, Cpu, RefreshCw, Activity, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export default function Dashboard() {
  return (
    <div className="space-y-8">
      <PageHeader 
        title="Control Plane Overview" 
        description="Centralized deterministic authorization and telemetry metrics for all financial AI agents."
      />

      {/* Overview Metric Cards Placeholder */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="border border-slate-800 bg-slate-900/10 rounded-xl p-6 backdrop-blur-sm relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-[2px] bg-cyan-500" />
          <div className="flex justify-between items-start mb-4">
            <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">Shield Protection</span>
            <Shield className="w-5 h-5 text-cyan-400" />
          </div>
          <div className="text-3xl font-extrabold text-white mb-1">Active</div>
          <p className="text-xs text-slate-400 leading-relaxed">AgentShield policy evaluation and action override guards are fully active.</p>
        </div>

        <div className="border border-slate-800 bg-slate-900/10 rounded-xl p-6 backdrop-blur-sm relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-[2px] bg-emerald-500" />
          <div className="flex justify-between items-start mb-4">
            <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">Connected Agents</span>
            <Cpu className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-white mb-1">3 / 3</div>
          <p className="text-xs text-slate-400 leading-relaxed">Fraud Detection, Payment Recovery, and Growth Incentives agents online.</p>
        </div>

        <div className="border border-slate-800 bg-slate-900/10 rounded-xl p-6 backdrop-blur-sm relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-[2px] bg-purple-500" />
          <div className="flex justify-between items-start mb-4">
            <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">Day Status</span>
            <Activity className="w-5 h-5 text-purple-400" />
          </div>
          <div className="text-3xl font-extrabold text-white mb-1">Buildathon Day 2</div>
          <p className="text-xs text-slate-400 leading-relaxed">Modular base infrastructure, operational schemas, and read API integrations completed.</p>
        </div>
      </div>

      {/* Main Grid Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Quick Sandboxes */}
        <div className="lg:col-span-2 border border-slate-800/80 bg-slate-950/20 rounded-xl p-6 backdrop-blur-sm space-y-6">
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            Control Plane Sandboxes
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border border-slate-900 hover:border-slate-800 bg-slate-900/10 rounded-lg p-5 transition-all">
              <h4 className="font-bold text-white text-sm mb-1.5">Interactive Sandbox Demo</h4>
              <p className="text-xs text-slate-400 leading-relaxed mb-4">Run live visual simulations of the dynamic Agent to Shield verification lifecycle.</p>
              <Link 
                href="/demo" 
                className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-semibold uppercase tracking-wider"
              >
                Go to Sandbox <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
            
            <div className="border border-slate-900 hover:border-slate-800 bg-slate-900/10 rounded-lg p-5 transition-all">
              <h4 className="font-bold text-white text-sm mb-1.5">Historical Logs Audit</h4>
              <p className="text-xs text-slate-400 leading-relaxed mb-4">View secure, non-destructive audit log records of completed agent proposals.</p>
              <Link 
                href="/audit-logs" 
                className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-semibold uppercase tracking-wider"
              >
                Review Log Trail <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>

        {/* System Specs panel */}
        <div className="border border-slate-800/80 bg-slate-950/20 rounded-xl p-6 backdrop-blur-sm space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider text-slate-400">Control Parameters</h3>
          <div className="space-y-3.5 divide-y divide-slate-900 text-xs">
            <div className="flex justify-between items-center py-2.5">
              <span className="text-slate-400">Auto Block Threshold</span>
              <span className="font-mono text-slate-200">0.90 Score</span>
            </div>
            <div className="flex justify-between items-center pt-3 pb-2.5">
              <span className="text-slate-400">Max Discount Limit</span>
              <span className="font-mono text-slate-200">10% Value</span>
            </div>
            <div className="flex justify-between items-center pt-3 pb-2.5">
              <span className="text-slate-400">Max Dunning Retries</span>
              <span className="font-mono text-slate-200">3 Retries</span>
            </div>
            <div className="flex justify-between items-center pt-3">
              <span className="text-slate-400">Database Engine</span>
              <span className="font-mono text-slate-200">Neon PostgreSQL</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
