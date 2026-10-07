import React from 'react';
import { Link } from 'react-router-dom';
import { errorMessage } from '@/lib/api/client';
import { usePipelineRun } from '@/lib/api/pipeline';
import { GATE_LABEL } from '@/lib/utils/constants';

/** MLE only: shows the Z3 counterexample. Compliance officers never see these
 * values; this route is not available to them. */
const ViolationReport: React.FC = () => {
  const { data: run, isLoading, isError, error } = usePipelineRun();

  if (isLoading) return <p className="text-sm text-slate-300">Loading the latest violations...</p>;
  if (isError) {
    return <p role="alert" className="text-sm text-red-300">{errorMessage(error)}</p>;
  }

  const failed = (run?.gates ?? []).filter((g) => g.violations.length > 0);
  if (!run || failed.length === 0) {
    return (
      <p className="rounded-lg border border-slate-800 bg-slate-900/50 p-6 text-sm text-slate-300">
        No violations in the latest run.{' '}
        <Link to="/pipeline" className="text-blue-400 underline">Back to the pipeline</Link>
      </p>
    );
  }

  return (
    <div className="space-y-6 text-sm">
      <p className="text-slate-300">
        Model <span className="font-mono text-white">{run.model_version}</span> did not pass.
      </p>
      {failed.map((gate) => (
        <section key={gate.gate} className="space-y-4">
          <h2 className="font-medium text-white">{GATE_LABEL[gate.gate]}</h2>
          {gate.violations.map((violation) => (
            <article key={violation.rule_id} className="rounded-xl border border-red-900 bg-red-950/20 p-5">
              <p className="font-mono text-red-200">{violation.rule_id}</p>
              <p className="mt-2 text-slate-200">{violation.plain_english}</p>
              {Object.keys(violation.counterexample).length > 0 && (
                <table className="mt-4 w-full max-w-md text-left">
                  <caption className="mb-1 text-left text-xs uppercase tracking-wide text-slate-400">
                    Z3 counterexample
                  </caption>
                  <tbody>
                    {Object.entries(violation.counterexample).map(([name, value]) => (
                      <tr key={name} className="border-t border-slate-800 font-mono">
                        <td className="py-1 pr-4 text-slate-300">{name}</td>
                        <td className="py-1 text-white">{value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </article>
          ))}
        </section>
      ))}
    </div>
  );
};

export default ViolationReport;
