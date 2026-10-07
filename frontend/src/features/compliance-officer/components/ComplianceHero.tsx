import React from 'react';
import { COMPLIANCE_STATUS, type ComplianceStatus } from '@/lib/status/complianceStatus';

const STYLES: Record<ComplianceStatus, { label: string; icon: string; box: string; dot: string }> = {
  [COMPLIANCE_STATUS.COMPLIANT]: { label: 'Compliant', icon: '✓', box: 'border-emerald-700 bg-emerald-950 text-emerald-100', dot: 'bg-emerald-500' },
  [COMPLIANCE_STATUS.VIOLATION]: { label: 'Violation', icon: '✗', box: 'border-red-700 bg-red-950 text-red-100', dot: 'bg-red-500 animate-pulse' },
  [COMPLIANCE_STATUS.PENDING]: { label: 'Needs attention', icon: '!', box: 'border-amber-700 bg-amber-950 text-amber-100', dot: 'bg-amber-500' },
  [COMPLIANCE_STATUS.UNKNOWN]: { label: 'Not yet certified', icon: '?', box: 'border-slate-600 bg-slate-900 text-slate-100', dot: 'bg-slate-400' },
};

interface Props {
  status: ComplianceStatus;
  headline: string;
  detail: string;
  live: boolean;
}

/** Full-width compliance status. Always colour, icon and text.
 * It is a live region so a change is announced without a page refresh. */
export const ComplianceHero: React.FC<Props> = ({ status, headline, detail, live }) => {
  const style = STYLES[status];
  return (
    <section
      role="status"
      aria-live="polite"
      className={`rounded-lg border-2 px-8 py-6 transition-colors duration-300 ${style.box}`}
    >
      <div className="flex items-center justify-between gap-4">
        <p className="flex items-center gap-3 text-2xl font-semibold">
          <span className={`h-3 w-3 rounded-full ${style.dot}`} aria-hidden="true" />
          <span aria-hidden="true">{style.icon}</span>
          {style.label}
        </p>
        <span className="text-sm opacity-80">{live ? 'Updating live' : 'Reconnecting...'}</span>
      </div>
      <p className="mt-2 text-lg">{headline}</p>
      <p className="text-base opacity-80">{detail}</p>
    </section>
  );
};
