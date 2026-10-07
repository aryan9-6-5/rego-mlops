import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { errorMessage } from '@/lib/api/client';
import {
  usePipelineRun,
  usePipelineSocket,
  useSubmitModel,
  useTriggerCT,
} from '@/lib/api/pipeline';
import { GATE_LABEL, GATE_STATUS } from '@/lib/utils/constants';
import { GateStatusBadge } from '../components/GateStatusBadge';

const INPUT = 'w-full rounded-lg border bg-slate-950 px-3 py-2 text-sm text-white';

const PipelineMonitor: React.FC = () => {
  const connected = usePipelineSocket();
  const { data: run, isLoading, isError, error } = usePipelineRun();
  const submit = useSubmitModel();
  const triggerCT = useTriggerCT();
  const [artifact, setArtifact] = useState('');
  const [artifactError, setArtifactError] = useState('');
  const [regulationVersion, setRegulationVersion] = useState('');
  const [versionError, setVersionError] = useState('');

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!artifact.trim()) return setArtifactError('Enter the model bundle folder name.');
    setArtifactError('');
    submit.mutate(artifact.trim());
  };

  const onTrigger = (event: React.FormEvent) => {
    event.preventDefault();
    if (!regulationVersion.trim()) return setVersionError('Enter a regulation version.');
    setVersionError('');
    triggerCT.mutate(regulationVersion.trim());
  };

  return (
    <div className="space-y-6 text-sm">
      <div className="grid gap-6 lg:grid-cols-2">
        <form onSubmit={onSubmit} noValidate className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
          <h2 className="font-medium text-white">Submit a model</h2>
          <input
            value={artifact}
            onChange={(e) => setArtifact(e.target.value)}
            placeholder="ct-RBI-4.1-20261007T000000Z"
            aria-label="Model bundle folder"
            aria-invalid={artifactError !== ''}
            className={`${INPUT} font-mono ${artifactError ? 'border-red-600' : 'border-slate-700'}`}
          />
          {artifactError && <p role="alert" className="text-red-300">{artifactError}</p>}
          {submit.isError && <p role="alert" className="text-red-300">{errorMessage(submit.error)}</p>}
          <button type="submit" disabled={submit.isPending} className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white enabled:hover:bg-blue-500 disabled:opacity-40">
            {submit.isPending ? 'Starting compliance gates...' : 'Run compliance gates'}
          </button>
        </form>

        <form onSubmit={onTrigger} noValidate className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
          <h2 className="font-medium text-white">Retrain for a regulation version</h2>
          <input
            value={regulationVersion}
            onChange={(e) => setRegulationVersion(e.target.value)}
            placeholder="RBI-4.1-20261007T000000Z"
            aria-label="Regulation version"
            aria-invalid={versionError !== ''}
            className={`${INPUT} font-mono ${versionError ? 'border-red-600' : 'border-slate-700'}`}
          />
          {versionError && <p role="alert" className="text-red-300">{versionError}</p>}
          {triggerCT.isError && <p role="alert" className="text-red-300">{errorMessage(triggerCT.error)}</p>}
          {triggerCT.isSuccess && <p role="status" className="text-emerald-300">Training workflow started in GitHub Actions.</p>}
          <button type="submit" disabled={triggerCT.isPending} className="rounded-lg border border-slate-600 px-4 py-2 font-medium text-slate-200 enabled:hover:bg-slate-800 disabled:opacity-40">
            {triggerCT.isPending ? 'Starting training workflow...' : 'Trigger retraining'}
          </button>
        </form>
      </div>

      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/50">
        <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <h2 className="font-medium text-white">
            Compliance gates{run ? <span className="ml-2 font-mono text-slate-400">{run.model_version}</span> : null}
          </h2>
          <span className={connected ? 'text-emerald-300' : 'text-amber-300'}>
            {connected ? 'Live' : 'Reconnecting...'}
          </span>
        </header>

        {isLoading && <p className="p-6 text-slate-300">Loading the latest pipeline run...</p>}
        {isError && <p role="alert" className="p-6 text-red-300">{errorMessage(error)}</p>}
        {!isLoading && !isError && !run && (
          <p className="p-6 text-slate-300">No model has been submitted yet. Submit a model bundle to run the gates.</p>
        )}

        {run && (
          <table className="w-full text-left">
            <thead className="bg-slate-800/50 text-slate-400">
              <tr>
                <th className="px-6 py-3 font-medium">Gate</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Duration</th>
                <th className="px-6 py-3 font-medium">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {run.gates.map((gate) => (
                <tr key={gate.gate} className="align-top">
                  <td className="px-6 py-3 text-white">{GATE_LABEL[gate.gate]}</td>
                  <td className="px-6 py-3"><GateStatusBadge status={gate.status} /></td>
                  <td className="px-6 py-3 font-mono text-slate-300">
                    {gate.status === GATE_STATUS.COMPLIANT || gate.status === GATE_STATUS.VIOLATION
                      ? `${Math.round(gate.duration_ms)} ms`
                      : '-'}
                  </td>
                  <td className="px-6 py-3 text-slate-300">{gate.plain_english}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {run?.status === GATE_STATUS.VIOLATION && (
          <p className="border-t border-slate-800 px-6 py-4">
            <Link to="/violation-report" className="text-blue-400 underline">View the violation report</Link>
          </p>
        )}
      </section>
    </div>
  );
};

export default PipelineMonitor;
