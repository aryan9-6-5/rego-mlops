import React from 'react';
import { Link } from 'react-router-dom';
import { errorMessage } from '@/lib/api/client';
import { useDriftLog } from '@/lib/api/insights';
import { formatDate, useModelLineages } from '@/lib/api/models';
import { usePipelineRun } from '@/lib/api/pipeline';
import { usePipelineEventsFeed, usePipelineEventsStore } from '@/lib/realtime/pipelineEvents';
import { GATE_LABEL, GATE_STATUS, type GateName, type GateStatus } from '@/lib/utils/constants';
import { GateStatusBadge } from '../components/GateStatusBadge';

const HISTORY_ROWS = 10;
const RECENT_MODELS = 5;

const Card: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
    <h2 className="mb-3 font-medium text-white">{title}</h2>
    {children}
  </section>
);

const Note: React.FC<{ children: React.ReactNode; error?: boolean }> = ({ children, error }) => (
  <p role={error ? 'alert' : undefined} className={error ? 'text-red-300' : 'text-slate-400'}>
    {children}
  </p>
);

const Dashboard: React.FC = () => {
  usePipelineEventsFeed();
  const run = usePipelineRun();
  const models = useModelLineages();
  const drift = useDriftLog();
  const { events, loaded, error: historyError, live } = usePipelineEventsStore();

  return (
    <div className="grid gap-6 text-sm xl:grid-cols-2">
      <Card title="Pipeline status">
        {run.isLoading && <Note>Loading the latest pipeline run...</Note>}
        {run.isError && <Note error>{errorMessage(run.error)}</Note>}
        {!run.isLoading && !run.isError && !run.data && (
          <Note>No model has been submitted yet. <Link to="/pipeline" className="text-blue-400 underline">Submit one</Link></Note>
        )}
        {run.data && (
          <div className="space-y-2">
            <p className="font-mono text-white">{run.data.model_version}</p>
            <ul className="space-y-1">
              {run.data.gates.map((g) => (
                <li key={g.gate} className="flex items-center justify-between">
                  <span className="text-slate-300">{GATE_LABEL[g.gate]}</span>
                  <GateStatusBadge status={g.status} />
                </li>
              ))}
            </ul>
            <Link to="/pipeline" className="text-blue-400 underline">Open the pipeline monitor</Link>
          </div>
        )}
      </Card>

      <Card title="Recent model versions">
        {models.isLoading && <Note>Loading model versions...</Note>}
        {models.isError && <Note error>{errorMessage(models.error)}</Note>}
        {models.data?.length === 0 && <Note>No model versions certified yet.</Note>}
        {models.data && models.data.length > 0 && (
          <ul className="space-y-1">
            {models.data.slice(0, RECENT_MODELS).map((m) => (
              <li key={m.model_version} className="flex justify-between">
                <span className="font-mono text-white">{m.model_version}</span>
                <span className="text-slate-400">
                  {m.regulation_versions.length} rules, {formatDate(m.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title={`CI gate history${live ? '' : ' (reconnecting...)'}`}>
        {!loaded && <Note>Loading gate history...</Note>}
        {historyError && <Note error>{historyError}</Note>}
        {loaded && !historyError && events.length === 0 && <Note>No gates have run yet.</Note>}
        {events.length > 0 && (
          <table className="w-full text-left">
            <tbody className="divide-y divide-slate-800">
              {events.slice(0, HISTORY_ROWS).map((e) => (
                <tr key={e.id}>
                  <td className="py-1 pr-3 font-mono text-slate-400">
                    {new Date(e.created_at).toLocaleTimeString()}
                  </td>
                  <td className="py-1 pr-3 font-mono text-white">{e.model_version}</td>
                  <td className="py-1 pr-3 text-slate-300">
                    {GATE_LABEL[e.gate_name as GateName] ?? e.gate_name}
                  </td>
                  <td className="py-1 pr-3"><GateStatusBadge status={e.status as GateStatus} /></td>
                  <td className="py-1 font-mono text-slate-400">
                    {e.status === GATE_STATUS.SKIPPED ? '-' : `${e.duration_ms} ms`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card title="Regulation drift log">
        {drift.isLoading && <Note>Loading recent regulation changes...</Note>}
        {drift.isError && <Note error>{errorMessage(drift.error)}</Note>}
        {drift.data?.length === 0 && <Note>No regulation versions yet.</Note>}
        {drift.data && drift.data.length > 0 && (
          <ul className="space-y-1">
            {drift.data.slice(0, HISTORY_ROWS).map((d) => (
              <li key={d.version_id} className="flex items-center justify-between gap-3">
                <span className="font-mono text-white">{d.version_id}</span>
                <span className={d.status === 'active' ? 'text-emerald-300' : 'text-slate-400'}>
                  {d.status === 'active' ? 'Active' : 'Superseded'}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
};

export default Dashboard;
