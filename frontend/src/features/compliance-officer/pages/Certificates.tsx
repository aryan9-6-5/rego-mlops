import React from 'react';
import { errorMessage } from '@/lib/api/client';
import { formatDate, useModelLineages } from '@/lib/api/models';
import type { RegulationStatus } from '@/lib/utils/constants';
import { StatusBadge } from '../components/ComplianceBadge';

/** Which regulation versions each deployed model was certified against. */
const Certificates: React.FC = () => {
  const { data, isLoading, isError, error } = useModelLineages();

  if (isLoading) {
    return <p className="text-slate-300">Loading certified models...</p>;
  }
  if (isError) {
    return (
      <p role="alert" className="rounded-lg border border-red-800 bg-red-950 p-4 text-red-200">
        {errorMessage(error)}
      </p>
    );
  }
  if (!data || data.length === 0) {
    return (
      <p className="mx-auto max-w-3xl rounded-lg border border-slate-800 bg-slate-900/50 p-6 text-base text-slate-300">
        No models have been certified yet. Certified models appear here after
        they pass every compliance check and are deployed.
      </p>
    );
  }

  return (
    <ul className="mx-auto max-w-3xl space-y-4 text-base">
      {data.map((model) => (
        <li key={model.model_version} className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
          <div className="flex items-baseline justify-between gap-4">
            <h2 className="text-lg font-semibold text-white">
              Model <span className="font-mono">{model.model_version}</span>
            </h2>
            <span className="text-sm text-slate-400">Certified {formatDate(model.created_at)}</span>
          </div>
          <p className="mt-3 text-sm uppercase tracking-wide text-slate-400">
            Certified against
          </p>
          <ul className="mt-2 space-y-2">
            {model.regulation_versions.map((reg) => (
              <li key={reg.version_id} className="flex items-center justify-between gap-4">
                <span className="text-slate-200">
                  RBI section {reg.section ?? reg.rule_id}
                  <span className="ml-2 font-mono text-sm text-slate-400">{reg.version_id}</span>
                </span>
                <StatusBadge status={reg.status as RegulationStatus} />
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
};

export default Certificates;
