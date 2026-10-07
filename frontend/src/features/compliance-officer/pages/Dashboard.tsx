import React from 'react';
import { errorMessage } from '@/lib/api/client';
import { useCertificates } from '@/lib/api/certificates';
import { useAuth } from '@/lib/auth/useAuth';
import { usePipelineEventsFeed, usePipelineEventsStore } from '@/lib/realtime/pipelineEvents';
import { deriveComplianceStatus } from '@/lib/status/complianceStatus';
import { REGULATION_STATUS } from '@/lib/utils/constants';
import { useRegulations } from '../api/regulations';
import { ComplianceHero } from '../components/ComplianceHero';
import {
  ActiveRulesList,
  Panel,
  PendingApprovals,
  RecentCertificates,
} from '../components/DashboardCards';

const RECENT_CERTIFICATES = 5;

const ErrorNote: React.FC<{ error: unknown }> = ({ error }) => (
  <p role="alert" className="text-red-200">{errorMessage(error)}</p>
);

const Dashboard: React.FC = () => {
  usePipelineEventsFeed();
  const { role } = useAuth();
  const { events, live, loaded } = usePipelineEventsStore();
  const regulations = useRegulations();
  const certificates = useCertificates();

  const rules = regulations.data ?? [];
  const active = rules.filter((r) => r.status === REGULATION_STATUS.ACTIVE);
  const pending = rules.filter((r) => r.status === REGULATION_STATUS.PENDING_APPROVAL);
  const ready = loaded && !regulations.isLoading && !certificates.isLoading;

  const status = deriveComplianceStatus({
    events,
    certificates: certificates.data ?? [],
    activeVersionIds: active.map((r) => `${r.rule_id}-${r.version}`),
  });

  return (
    <div className="mx-auto max-w-[1200px] space-y-8 text-base">
      {ready ? (
        <ComplianceHero
          status={status.status}
          headline={status.headline}
          detail={status.detail}
          live={live}
        />
      ) : (
        <p role="status" className="rounded-lg border border-slate-800 p-6 text-slate-300">
          Checking your current compliance status...
        </p>
      )}

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Panel title="Rules in force">
            {regulations.isLoading && <p className="text-slate-300">Loading the rules in force...</p>}
            {regulations.isError && <ErrorNote error={regulations.error} />}
            {regulations.data && <ActiveRulesList rules={active} />}
          </Panel>
        </div>
        <Panel title="Waiting for your review">
          {regulations.isLoading && <p className="text-slate-300">Counting rules to review...</p>}
          {regulations.isError && <ErrorNote error={regulations.error} />}
          {regulations.data && (
            <PendingApprovals pending={pending} canReview={role === 'compliance_officer'} />
          )}
        </Panel>
      </div>

      <Panel title="Recent certificates">
        {certificates.isLoading && <p className="text-slate-300">Loading recent certificates...</p>}
        {certificates.isError && <ErrorNote error={certificates.error} />}
        {certificates.data && (
          <RecentCertificates certificates={certificates.data.slice(0, RECENT_CERTIFICATES)} />
        )}
      </Panel>
    </div>
  );
};

export default Dashboard;
