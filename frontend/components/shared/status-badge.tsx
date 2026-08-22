import React from 'react';

export type BadgeType = 
  | 'ACTIVE' | 'INACTIVE'
  | 'SUCCESS' | 'FAILED' | 'PENDING' | 'BLOCKED'
  | 'REVIEWED' | 'EXECUTED' | 'REJECTED'
  | 'APPROVE' | 'MODIFY' | 'ESCALATE'
  | 'PASSED' | 'WARNING';

interface StatusBadgeProps {
  status: BadgeType | string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const upperStatus = status.toUpperCase();

  let styles = 'bg-slate-800 text-slate-300 border-slate-700';
  let label = status;

  switch (upperStatus) {
    // Agent
    case 'ACTIVE':
    case 'PASSED':
    case 'SUCCESS':
    case 'APPROVE':
      styles = 'bg-emerald-950/40 text-emerald-400 border-emerald-800/50';
      label = upperStatus === 'APPROVE' ? 'APPROVED' : upperStatus;
      break;

    case 'PENDING':
      styles = 'bg-amber-950/40 text-amber-400 border-amber-800/50';
      label = 'PENDING';
      break;

    case 'FAILED':
    case 'BLOCKED':
    case 'REJECTED':
    case 'REJECT':
      styles = 'bg-rose-950/40 text-rose-400 border-rose-800/50';
      label = upperStatus === 'REJECT' ? 'REJECTED' : upperStatus;
      break;

    case 'INACTIVE':
      styles = 'bg-slate-800/60 text-slate-400 border-slate-700/60';
      label = 'INACTIVE';
      break;

    case 'REVIEWED':
    case 'MODIFY':
      styles = 'bg-cyan-950/40 text-cyan-400 border-cyan-800/50';
      label = upperStatus === 'MODIFY' ? 'MODIFIED' : upperStatus;
      break;

    case 'EXECUTED':
      styles = 'bg-blue-950/40 text-blue-400 border-blue-800/50';
      label = 'EXECUTED';
      break;

    case 'ESCALATE':
      styles = 'bg-purple-950/40 text-purple-400 border-purple-800/50';
      label = 'ESCALATED';
      break;

    case 'WARNING':
      styles = 'bg-orange-950/40 text-orange-400 border-orange-800/50';
      label = 'WARNING';
      break;
      
    default:
      break;
  }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold tracking-wide border uppercase ${styles}`} aria-label={`Status: ${label}`}>
      {label}
    </span>
  );
}
