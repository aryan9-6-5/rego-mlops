import React from 'react';
import { GATE_STATUS, type GateStatus } from '@/lib/utils/constants';

const STYLES: Record<GateStatus, { label: string; className: string; dot: string }> = {
  [GATE_STATUS.QUEUED]: { label: 'Queued', className: 'bg-slate-800 text-slate-300 border-slate-600', dot: 'bg-slate-400' },
  [GATE_STATUS.RUNNING]: { label: 'Running', className: 'bg-blue-950 text-blue-300 border-blue-800', dot: 'bg-blue-500 animate-pulse' },
  [GATE_STATUS.COMPLIANT]: { label: 'Compliant', className: 'bg-emerald-950 text-emerald-300 border-emerald-800', dot: 'bg-emerald-500' },
  [GATE_STATUS.VIOLATION]: { label: 'Violation', className: 'bg-red-950 text-red-300 border-red-800', dot: 'bg-red-500 animate-pulse' },
  [GATE_STATUS.SKIPPED]: { label: 'Skipped', className: 'bg-slate-900 text-slate-400 border-slate-700', dot: 'bg-slate-600' },
};

/** Colour AND text label, never colour alone. */
export const GateStatusBadge: React.FC<{ status: GateStatus }> = ({ status }) => {
  const style = STYLES[status];
  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${style.className}`}>
      <span className={`h-2 w-2 rounded-full ${style.dot}`} aria-hidden="true" />
      {style.label}
    </span>
  );
};
