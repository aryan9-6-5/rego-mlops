import React from 'react';
import { Link } from 'react-router-dom';
import { downloadCertificate } from '@/lib/api/certificates';
import type { Certificate } from '@/lib/api/certificateHelpers';
import { formatDate } from '@/lib/api/models';
import { regulationLabel, regulationVersionLabel } from '@/lib/utils/regulationLabels';
import type { Regulation } from '../api/regulations';

const PANEL = 'rounded-lg border border-slate-800 bg-slate-900/50 p-6';

export const Panel: React.FC<{ title: string; children: React.ReactNode }> = ({
  title,
  children,
}) => (
  <section className={PANEL}>
    <h2 className="mb-4 text-xl font-semibold text-white">{title}</h2>
    {children}
  </section>
);

export const ActiveRulesList: React.FC<{ rules: Regulation[] }> = ({ rules }) =>
  rules.length === 0 ? (
    <p className="text-slate-300">No rules are active yet. Add a regulation to get started.</p>
  ) : (
    <ul className="space-y-4">
      {rules.map((rule) => (
        <li key={rule.id}>
          <p className="font-medium text-slate-100">
            {regulationVersionLabel(rule.rule_id, `${rule.rule_id}-${rule.version}`)}
          </p>
          <p className="text-slate-300">{rule.description ?? 'No summary available.'}</p>
        </li>
      ))}
    </ul>
  );

export const PendingApprovals: React.FC<{ pending: Regulation[]; canReview: boolean }> = ({
  pending,
  canReview,
}) => (
  <div>
    <p className="text-4xl font-semibold text-white">{pending.length}</p>
    <p className="mb-4 text-slate-300">
      {pending.length === 1 ? 'rule is' : 'rules are'} waiting for your review
    </p>
    {pending.length > 0 && canReview && (
      <Link
        to="/approval-queue"
        className="inline-flex h-12 items-center rounded-md bg-indigo-600 px-5 font-medium text-white hover:bg-indigo-500"
      >
        Review now
      </Link>
    )}
  </div>
);

export const RecentCertificates: React.FC<{ certificates: Certificate[] }> = ({
  certificates,
}) =>
  certificates.length === 0 ? (
    <p className="text-slate-300">
      No certificates yet. One is issued when a model passes every compliance check.
    </p>
  ) : (
    <table className="w-full text-left text-base">
      <thead className="text-sm uppercase tracking-wide text-slate-400">
        <tr>
          <th className="py-2 pr-4 font-medium">Issued</th>
          <th className="py-2 pr-4 font-medium">Model</th>
          <th className="py-2 pr-4 font-medium">Certified against</th>
          <th className="py-2 font-medium"><span className="sr-only">Download</span></th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-800">
        {certificates.map((cert) =>
          cert.verification === 'tampered' ? (
            <tr key={cert.id}>
              <td className="py-3 pr-4 text-slate-300">{formatDate(cert.created_at)}</td>
              <td className="py-3 pr-4 font-mono text-slate-100">{cert.model_version}</td>
              <td colSpan={2} className="py-3 text-red-200">Verification failed. Contact your administrator.</td>
            </tr>
          ) : (
            <tr key={cert.id}>
              <td className="py-3 pr-4 text-slate-300">{formatDate(cert.created_at)}</td>
              <td className="py-3 pr-4 font-mono text-slate-100">{cert.model_version}</td>
              <td className="py-3 pr-4 text-slate-200">
                {cert.regulation_versions.map((r) => regulationLabel(r.rule_id)).join(', ')}
              </td>
              <td className="py-3 text-right">
                <button
                  type="button"
                  onClick={() => downloadCertificate(cert)}
                  className="h-10 rounded-md border border-slate-600 px-4 text-slate-200 hover:bg-slate-800"
                >
                  Download
                </button>
              </td>
            </tr>
          ),
        )}
      </tbody>
    </table>
  );
