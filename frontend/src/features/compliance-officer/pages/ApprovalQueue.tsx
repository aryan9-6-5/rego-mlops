import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { errorMessage } from '@/lib/api/client';
import { REGULATION_STATUS } from '@/lib/utils/constants';
import { regulationVersionLabel } from '@/lib/utils/regulationLabels';
import { useRegulations } from '../api/regulations';
import { StatusBadge } from '../components/ComplianceBadge';
import { RuleReviewCard } from '../components/RuleReviewCard';

const ApprovalQueue: React.FC = () => {
  const { data, isLoading, isError, error } = useRegulations();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  if (isLoading) {
    return <p className="text-slate-300">Loading rules awaiting your review...</p>;
  }
  if (isError) {
    return (
      <p role="alert" className="rounded-lg border border-red-800 bg-red-950 p-4 text-red-200">
        {errorMessage(error)}
      </p>
    );
  }

  const rules = data ?? [];
  const pending = rules.filter((r) => r.status === REGULATION_STATUS.PENDING_APPROVAL);
  const failed = rules.filter((r) => r.status === REGULATION_STATUS.Z3_REJECTED);
  const active = rules.filter((r) => r.status === REGULATION_STATUS.ACTIVE);
  const selected = pending.find((r) => r.id === selectedId);

  if (selected) {
    return (
      <div className="mx-auto max-w-5xl space-y-4">
        <button type="button" onClick={() => setSelectedId(null)} className="text-slate-300 hover:text-white">
          ← Back to queue
        </button>
        <RuleReviewCard regulation={selected} onDone={() => setSelectedId(null)} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-10 text-base">
      <section>
        <h2 className="mb-4 text-xl font-semibold text-white">Awaiting your review</h2>
        {pending.length === 0 ? (
          <p className="rounded-lg border border-slate-800 bg-slate-900/50 p-6 text-slate-300">
            No rules are waiting for review.{' '}
            <Link to="/regulations" className="text-blue-400 underline">
              Add a regulation
            </Link>
          </p>
        ) : (
          <ul className="space-y-3">
            {pending.map((rule) => (
              <li key={rule.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(rule.id)}
                  className="flex w-full items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/50 p-5 text-left hover:border-slate-600"
                >
                  <span>
                    <span className="block text-sm text-slate-400">{regulationVersionLabel(rule.rule_id, `${rule.rule_id}-${rule.version}`)}</span>
                    <span className="block text-slate-100">{rule.description ?? 'Review rule'}</span>
                  </span>
                  <StatusBadge status={rule.status} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {failed.length > 0 && (
        <section>
          <h2 className="mb-4 text-xl font-semibold text-white">Could not be verified</h2>
          <ul className="space-y-3">
            {failed.map((rule) => (
              <li key={rule.id} className="rounded-xl border border-red-900 bg-red-950/30 p-5">
                <div className="flex items-center justify-between gap-4">
                  <span className="text-sm text-slate-400">{regulationVersionLabel(rule.rule_id, `${rule.rule_id}-${rule.version}`)}</span>
                  <StatusBadge status={rule.status} />
                </div>
                <p className="mt-2 text-red-100">
                  {rule.validation_message ?? 'The AI draft was not a valid rule.'}
                </p>
                <p className="mt-1 text-sm text-slate-400">
                  This is an AI extraction error, not a problem with your regulation text. Please try again.
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {active.length > 0 && (
        <section>
          <h2 className="mb-4 text-xl font-semibold text-white">Active rules</h2>
          <ul className="space-y-2">
            {active.map((rule) => (
              <li key={rule.id} className="flex items-center justify-between gap-4 rounded-lg border border-slate-800 p-4">
                <span className="text-slate-200">
                  <span className="text-sm text-slate-400">{regulationVersionLabel(rule.rule_id, `${rule.rule_id}-${rule.version}`)}</span>{' '}
                  {rule.description}
                </span>
                <StatusBadge status={rule.status} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
};

export default ApprovalQueue;
