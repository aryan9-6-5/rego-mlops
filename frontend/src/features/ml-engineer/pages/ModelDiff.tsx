import React, { useState } from 'react';
import { errorMessage } from '@/lib/api/client';
import { useModelDiff, type FeatureChange } from '@/lib/api/insights';
import { useModelLineages } from '@/lib/api/models';

const KIND_STYLE: Record<FeatureChange['kind'], { label: string; className: string }> = {
  added: { label: 'Added', className: 'bg-emerald-950 text-emerald-300 border-emerald-800' },
  removed: { label: 'Removed', className: 'bg-amber-950 text-amber-300 border-amber-800' },
  changed: { label: 'Re-weighted', className: 'bg-blue-950 text-blue-300 border-blue-800' },
};

const fmt = (value: number | null): string => (value === null ? '-' : String(value));
const INPUT = 'w-64 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-white';

const ModelDiff: React.FC = () => {
  const models = useModelLineages();
  const [fromVersion, setFromVersion] = useState('');
  const [toVersion, setToVersion] = useState('');
  const diff = useModelDiff(fromVersion.trim(), toVersion.trim());

  return (
    <div className="space-y-6 text-sm">
      <datalist id="model-versions">
        {(models.data ?? []).map((m) => (
          <option key={m.model_version} value={m.model_version} />
        ))}
      </datalist>
      <div className="flex flex-wrap items-end gap-4">
        <label className="block">
          <span className="mb-1 block text-slate-300">From version</span>
          <input list="model-versions" value={fromVersion} onChange={(e) => setFromVersion(e.target.value)} className={INPUT} />
        </label>
        <label className="block">
          <span className="mb-1 block text-slate-300">To version</span>
          <input list="model-versions" value={toVersion} onChange={(e) => setToVersion(e.target.value)} className={INPUT} />
        </label>
      </div>

      {!diff.isFetching && fromVersion === '' && toVersion === '' && (
        <p className="text-slate-400">Choose two model versions to compare the features they use.</p>
      )}
      {diff.isFetching && (
        <p role="status" className="text-slate-300">Comparing the two models against the active rules...</p>
      )}
      {diff.isError && <p role="alert" className="text-red-300">{errorMessage(diff.error)}</p>}
      {diff.data && diff.data.changes.length === 0 && (
        <p className="text-slate-300">These two models use the same features with the same weights.</p>
      )}

      {diff.data && diff.data.changes.length > 0 && (
        <table className="w-full overflow-hidden rounded-2xl border border-slate-800 text-left">
          <thead className="bg-slate-800/50 text-slate-400">
            <tr>
              <th className="px-4 py-3 font-medium">Feature</th>
              <th className="px-4 py-3 font-medium">Change</th>
              <th className="px-4 py-3 font-medium">Weight before</th>
              <th className="px-4 py-3 font-medium">Weight after</th>
              <th className="px-4 py-3 font-medium">Regulatory impact</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {diff.data.changes.map((c) => {
              const impact = c.affects_rules.length > 0;
              return (
                <tr key={c.feature} className={impact ? 'bg-red-950/30' : ''}>
                  <td className="px-4 py-3 font-mono text-white">{c.feature}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full border px-3 py-1 text-xs font-medium ${KIND_STYLE[c.kind].className}`}>
                      {KIND_STYLE[c.kind].label}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-300">{fmt(c.before)}</td>
                  <td className="px-4 py-3 font-mono text-slate-300">{fmt(c.after)}</td>
                  <td className="px-4 py-3">
                    {impact ? (
                      <span className="font-medium text-red-300">
                        Affects {c.affects_rules.join(', ')}
                      </span>
                    ) : (
                      <span className="text-slate-400">No rule affected</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default ModelDiff;
