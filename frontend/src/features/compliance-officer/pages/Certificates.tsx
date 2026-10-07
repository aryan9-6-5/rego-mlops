import React from 'react';
import { errorMessage } from '@/lib/api/client';
import {
  downloadCertificate,
  regulationLabel,
  useCertificates,
} from '@/lib/api/certificates';
import { formatDate } from '@/lib/api/models';

/** Which regulation versions each certified model was checked against.
 * Proof hashes stay off this screen; they are in the download. */
const Certificates: React.FC = () => {
  const { data, isLoading, isError, error } = useCertificates();

  if (isLoading) {
    return <p className="text-slate-300">Loading certificates...</p>;
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
        No certificates have been issued yet. A certificate is issued when a
        model passes every compliance check and is deployed.
      </p>
    );
  }

  return (
    <ul className="mx-auto max-w-3xl space-y-4 text-base">
      {data.map((cert) => {
        const tampered = cert.verification === 'tampered';
        return (
          <li key={cert.id} className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-white">
                  Model <span className="font-mono">{cert.model_version}</span>
                </h2>
                <p className="text-sm text-slate-400">Issued {formatDate(cert.created_at)}</p>
              </div>
              {tampered ? (
                <span className="inline-flex items-center gap-2 rounded-full border border-red-800 bg-red-950 px-3 py-1 text-sm font-medium text-red-300">
                  <span className="h-2 w-2 rounded-full bg-red-500" aria-hidden="true" />
                  Verification failed
                </span>
              ) : (
                <span className="inline-flex items-center gap-2 rounded-full border border-emerald-800 bg-emerald-950 px-3 py-1 text-sm font-medium text-emerald-300">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" aria-hidden="true" />
                  Verified
                </span>
              )}
            </div>

            {tampered ? (
              <p role="alert" className="mt-4 text-red-200">
                This certificate does not match its signature and may have been
                altered. It cannot be shown or downloaded. Please contact your administrator.
              </p>
            ) : (
              <>
                <p className="mt-4 text-sm uppercase tracking-wide text-slate-400">
                  Certified against
                </p>
                <ul className="mt-2 space-y-1 text-slate-200">
                  {cert.regulation_versions.map((reg) => (
                    <li key={reg.version_id}>{regulationLabel(reg.rule_id)}</li>
                  ))}
                </ul>
                <button
                  type="button"
                  onClick={() => downloadCertificate(cert)}
                  className="mt-4 h-12 rounded-lg border border-slate-600 px-5 font-medium text-slate-200 hover:bg-slate-800"
                >
                  Download certificate
                </button>
              </>
            )}
          </li>
        );
      })}
    </ul>
  );
};

export default Certificates;
