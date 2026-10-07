import React, { useState } from 'react';
import { errorMessage } from '@/lib/api/client';
import { ACTIVATE_CONFIRMATION_WORD } from '@/lib/utils/constants';
import {
  useApproveRegulation,
  useRejectRegulation,
  type Regulation,
} from '../api/regulations';
import { readableRule } from '../lib/readableRule';
import { regulationVersionLabel } from '@/lib/utils/regulationLabels';
import { StatusBadge } from './ComplianceBadge';

type Step = 'review' | 'confirm-approve' | 'confirm-reject';

interface Props {
  regulation: Regulation;
  onDone: () => void;
}

const SECONDARY_BTN = 'px-4 text-slate-300 hover:text-white';

/** Two deliberate actions to approve or reject. */
export const RuleReviewCard: React.FC<Props> = ({ regulation, onDone }) => {
  const [step, setStep] = useState<Step>('review');
  const [typed, setTyped] = useState('');
  const [reason, setReason] = useState('');
  const approve = useApproveRegulation();
  const reject = useRejectRegulation();
  const error = approve.error ?? reject.error;
  const busy = approve.isPending || reject.isPending;

  const confirmApprove = () => approve.mutate(regulation.id, { onSuccess: onDone });
  const confirmReject = () =>
    reject.mutate({ id: regulation.id, reason }, { onSuccess: onDone });

  return (
    <section className="space-y-6 rounded-2xl border border-slate-800 bg-slate-900/50 p-8 text-base">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-slate-400">
            {regulationVersionLabel(regulation.rule_id, `${regulation.rule_id}-${regulation.version}`)}
          </p>
          <h2 className="text-xl font-semibold text-white">Review this rule</h2>
        </div>
        <StatusBadge status={regulation.status} />
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Your regulation text
          </h3>
          <p className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 leading-relaxed text-slate-200">
            {regulation.source_text}
          </p>
        </div>
        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
            What this rule means
          </h3>
          <p className="rounded-lg bg-slate-950 p-4 leading-relaxed text-slate-200">
            {regulation.description ?? 'No plain-English summary was provided.'}
          </p>
          <div className="mt-3 text-sm">
            <p className="font-semibold uppercase tracking-wide text-slate-400">
              The exact condition that will be checked
            </p>
            <p className="mt-1 rounded-lg bg-slate-950 p-3 text-slate-200">
              {readableRule(regulation.formal_logic) ??
                'This condition cannot be shown in plain words. Reject it and try again.'}
            </p>
          </div>
        </div>
      </div>

      <p className="text-slate-300">
        Does this correctly capture the regulation&apos;s intent?
      </p>

      {step === 'review' && (
        <div className="flex gap-4">
          <button
            type="button"
            onClick={() => setStep('confirm-approve')}
            className="h-12 rounded-lg bg-emerald-700 px-6 font-medium text-white hover:bg-emerald-600"
          >
            Yes, approve rule
          </button>
          <button
            type="button"
            onClick={() => setStep('confirm-reject')}
            className="h-12 rounded-lg border border-red-700 px-6 font-medium text-red-300 hover:bg-red-950"
          >
            No, reject rule
          </button>
        </div>
      )}

      {step === 'confirm-approve' && (
        <div className="space-y-4 rounded-lg border border-amber-800 bg-amber-950/40 p-5">
          <p className="text-amber-200">
            Once active, every future model deployment must satisfy this rule or
            deployment will be blocked.
          </p>
          <label className="block">
            <span className="mb-1 block text-sm text-slate-300">
              Type {ACTIVATE_CONFIRMATION_WORD} to confirm
            </span>
            <input
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              className="w-full max-w-xs rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-white"
              autoComplete="off"
            />
          </label>
          <div className="flex gap-3">
            <button
              type="button"
              disabled={typed !== ACTIVATE_CONFIRMATION_WORD || busy}
              onClick={confirmApprove}
              className="h-12 rounded-lg bg-emerald-700 px-6 font-medium text-white enabled:hover:bg-emerald-600 disabled:opacity-40"
            >
              {approve.isPending
                ? 'Activating rule and updating knowledge graph...'
                : 'Activate rule'}
            </button>
            <button type="button" disabled={busy} onClick={() => setStep('review')} className={SECONDARY_BTN}>
              Go back
            </button>
          </div>
        </div>
      )}

      {step === 'confirm-reject' && (
        <div className="space-y-4 rounded-lg border border-red-900 bg-red-950/30 p-5">
          <label className="block">
            <span className="mb-1 block text-sm text-slate-300">Reason (optional)</span>
            <textarea
              value={reason}
              maxLength={500}
              onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white"
              rows={2}
            />
          </label>
          <div className="flex gap-3">
            <button
              type="button"
              disabled={busy}
              onClick={confirmReject}
              className="h-12 rounded-lg bg-red-700 px-6 font-medium text-white enabled:hover:bg-red-600 disabled:opacity-40"
            >
              {reject.isPending ? 'Rejecting rule...' : 'Confirm rejection'}
            </button>
            <button type="button" disabled={busy} onClick={() => setStep('review')} className={SECONDARY_BTN}>
              Go back
            </button>
          </div>
        </div>
      )}

      {error && (
        <p role="alert" className="rounded-lg border border-red-800 bg-red-950 p-3 text-red-200">
          {errorMessage(error)}
        </p>
      )}
    </section>
  );
};
