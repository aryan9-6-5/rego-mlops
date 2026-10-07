import React from 'react';
import { REGULATION_STATUS, type RegulationStatus } from '@/lib/utils/constants';

interface BadgeStyle {
  label: string;
  className: string;
  dot: string;
}

const AMBER = 'bg-amber-950 text-amber-300 border-amber-800';
const GREEN = 'bg-emerald-950 text-emerald-300 border-emerald-800';
const RED = 'bg-red-950 text-red-300 border-red-800';
const BLUE = 'bg-blue-950 text-blue-300 border-blue-800';

const STYLES: Record<RegulationStatus, BadgeStyle> = {
  [REGULATION_STATUS.PENDING_APPROVAL]: { label: 'Pending Approval', className: AMBER, dot: 'bg-amber-500' },
  [REGULATION_STATUS.ACTIVE]: { label: 'Active', className: GREEN, dot: 'bg-emerald-500' },
  [REGULATION_STATUS.APPROVED]: { label: 'Approved, activating', className: BLUE, dot: 'bg-blue-500 animate-pulse' },
  [REGULATION_STATUS.REJECTED]: { label: 'Rejected', className: RED, dot: 'bg-red-500' },
  [REGULATION_STATUS.Z3_REJECTED]: { label: 'Verification Failed', className: RED, dot: 'bg-red-500' },
  [REGULATION_STATUS.EXTRACTED]: { label: 'Processing', className: BLUE, dot: 'bg-blue-500 animate-pulse' },
  [REGULATION_STATUS.Z3_VALIDATED]: { label: 'Processing', className: BLUE, dot: 'bg-blue-500 animate-pulse' },
};

/** Status is always colour AND text. */
export const StatusBadge: React.FC<{ status: RegulationStatus }> = ({ status }) => {
  const style = STYLES[status];
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium ${style.className}`}
    >
      <span className={`h-2 w-2 rounded-full ${style.dot}`} aria-hidden="true" />
      {style.label}
    </span>
  );
};
