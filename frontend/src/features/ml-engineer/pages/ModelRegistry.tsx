import React from 'react';
import { StatusBadge } from '@/features/compliance-officer/components/ComplianceBadge';
import { errorMessage } from '@/lib/api/client';
import { formatDate, useModelLineages } from '@/lib/api/models';
import type { RegulationStatus } from '@/lib/utils/constants';

const ModelRegistry: React.FC = () => {
  const { data, isLoading, isError, error } = useModelLineages();

  if (isLoading) {
    return <p className="text-slate-300">Loading model versions and their regulation lineage...</p>;
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
      <p className="rounded-lg border border-slate-800 bg-slate-900/50 p-6 text-slate-300">
        No model versions have been certified yet. A model appears here after it
        passes every compliance gate and is deployed.
      </p>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/50">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-800/50 text-slate-400">
          <tr>
            <th className="px-6 py-4 font-medium uppercase tracking-wider">Model version</th>
            <th className="px-6 py-4 font-medium uppercase tracking-wider">Certified</th>
            <th className="px-6 py-4 font-medium uppercase tracking-wider">Regulation versions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {data.map((model) => (
            <tr key={model.model_version} className="align-top">
              <td className="px-6 py-4 font-mono text-white">{model.model_version}</td>
              <td className="px-6 py-4 text-slate-300">{formatDate(model.created_at)}</td>
              <td className="space-y-2 px-6 py-4">
                {model.regulation_versions.length === 0 && (
                  <span className="text-slate-400">No linked regulation versions</span>
                )}
                {model.regulation_versions.map((reg) => (
                  <div key={reg.version_id} className="flex items-center gap-3">
                    <span className="font-mono text-slate-200">{reg.version_id}</span>
                    <StatusBadge status={reg.status as RegulationStatus} />
                  </div>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ModelRegistry;
