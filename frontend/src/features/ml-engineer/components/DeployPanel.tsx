import React, { useState } from 'react';
import { errorMessage } from '@/lib/api/client';
import { useDeployModel } from '@/lib/api/certificates';

interface Props {
  modelVersion: string;
}

/** Shown only after every gate is compliant. The server re-checks this and
 * refuses the deploy otherwise: there is no way to skip a gate. */
export const DeployPanel: React.FC<Props> = ({ modelVersion }) => {
  const [confirming, setConfirming] = useState(false);
  const deploy = useDeployModel();

  if (deploy.isSuccess) {
    return (
      <p role="status" className="border-t border-slate-800 px-6 py-4 text-emerald-300">
        Deployed. Certificate <span className="font-mono">{deploy.data.certificate_id}</span> issued.
      </p>
    );
  }

  return (
    <div className="space-y-3 border-t border-slate-800 px-6 py-4">
      {!confirming ? (
        <button
          type="button"
          onClick={() => setConfirming(true)}
          className="rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-500"
        >
          Deploy this model
        </button>
      ) : (
        <div className="space-y-3">
          <p className="text-slate-200">
            Deploy <span className="font-mono">{modelVersion}</span> and issue its
            compliance certificate? A certificate cannot be changed or removed.
          </p>
          <div className="flex gap-3">
            <button
              type="button"
              disabled={deploy.isPending}
              onClick={() => deploy.mutate(modelVersion)}
              className="rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white enabled:hover:bg-emerald-500 disabled:opacity-40"
            >
              {deploy.isPending
                ? 'Verifying with Z3, issuing certificate, running canary...'
                : 'Confirm deploy'}
            </button>
            <button
              type="button"
              disabled={deploy.isPending}
              onClick={() => setConfirming(false)}
              className="px-4 text-slate-300 hover:text-white"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      {deploy.isError && (
        <p role="alert" className="text-red-300">{errorMessage(deploy.error)}</p>
      )}
    </div>
  );
};
