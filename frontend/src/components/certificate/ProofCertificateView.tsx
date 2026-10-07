import React, { useState } from 'react';
import { downloadCertificate } from '@/lib/api/certificates';
import type { Certificate } from '@/lib/api/certificateHelpers';
import { regulationLabel, regulationVersionLabel } from '@/lib/utils/regulationLabels';

interface Props {
  certificate: Certificate;
  /** The ML engineer's view shows version ids, the full proof hash and the Z3
   * footer. The compliance officer's view is plain English with no hash on
   * screen; they can still copy it for an auditor. */
  technicalView: boolean;
}

type CopyState = 'idle' | 'copied' | 'failed';

export const ProofCertificateView: React.FC<Props> = ({ certificate, technicalView }) => {
  const [copy, setCopy] = useState<CopyState>('idle');

  const copyHash = async () => {
    try {
      await navigator.clipboard.writeText(certificate.proof_hash);
      setCopy('copied');
    } catch {
      setCopy('failed');
    }
  };

  const issued = certificate.created_at
    ? new Date(certificate.created_at).toLocaleString()
    : 'Unknown date';

  return (
    <article className="space-y-4 rounded-lg border border-indigo-800 bg-indigo-950/60 p-6">
      <header>
        <p className="text-sm uppercase tracking-wide text-indigo-300">Proof certificate</p>
        <h3 className="text-lg font-semibold text-white">
          Model <span className="font-mono">{certificate.model_version}</span>
        </h3>
      </header>

      <div>
        <p className="text-sm uppercase tracking-wide text-indigo-300">Certified against</p>
        <ul className="mt-1 space-y-1">
          {certificate.regulation_versions.map((reg) => (
            <li key={reg.version_id} className="text-slate-100">
              {technicalView ? regulationLabel(reg.rule_id) : regulationVersionLabel(reg.rule_id, reg.version_id)}
              {technicalView && (
                <code className="ml-2 rounded bg-indigo-950 px-1.5 py-0.5 font-mono text-xs text-indigo-300">
                  {reg.version_id}
                </code>
              )}
            </li>
          ))}
        </ul>
      </div>

      {technicalView && (
        <div>
          <p className="text-sm uppercase tracking-wide text-indigo-300">Z3 proof hash</p>
          <code className="mt-1 block break-all font-mono text-xs text-slate-200">
            {certificate.proof_hash}
          </code>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => downloadCertificate(certificate)}
          className="h-12 rounded-md bg-indigo-600 px-5 font-medium text-white hover:bg-indigo-500"
        >
          Download certificate
        </button>
        <button
          type="button"
          onClick={copyHash}
          className="h-12 rounded-md border border-indigo-500 px-5 font-medium text-indigo-200 hover:bg-indigo-900"
        >
          Copy hash
        </button>
        <span role="status" className="text-sm">
          {copy === 'copied' && <span className="text-emerald-300">Hash copied</span>}
          {copy === 'failed' && (
            <span className="text-red-300">
              Could not copy. Download the certificate instead.
            </span>
          )}
        </span>
      </div>

      <footer className="border-t border-indigo-900 pt-3 text-sm text-indigo-300">
        Issued {issued}. {technicalView ? 'Verified by Z3 SMT Solver.' : 'Checked automatically against every active rule.'}
      </footer>
    </article>
  );
};
