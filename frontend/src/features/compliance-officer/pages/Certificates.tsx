import React from 'react';
import { errorMessage } from '@/lib/api/client';
import { ProofCertificateView } from '@/components/certificate/ProofCertificateView';
import { useCertificates } from '@/lib/api/certificates';

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
      {data.map((cert) =>
        cert.verification === 'tampered' ? (
          <li key={cert.id} className="rounded-xl border border-red-900 bg-red-950/30 p-6">
            <h2 className="text-lg font-semibold text-white">
              Model <span className="font-mono">{cert.model_version}</span>
            </h2>
            <p role="alert" className="mt-2 text-red-200">
              Verification failed. This certificate does not match its signature and may
              have been altered, so it cannot be shown or downloaded. Please contact your
              administrator.
            </p>
          </li>
        ) : (
          <li key={cert.id}>
            <ProofCertificateView certificate={cert} technicalView={false} />
          </li>
        ),
      )}
    </ul>
  );
};

export default Certificates;
