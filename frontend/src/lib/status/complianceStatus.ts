import { GATE_STATUS } from '@/lib/utils/constants';

export const COMPLIANCE_STATUS = {
  COMPLIANT: 'compliant',
  VIOLATION: 'violation',
  PENDING: 'pending',
  UNKNOWN: 'unknown',
} as const;

export type ComplianceStatus = (typeof COMPLIANCE_STATUS)[keyof typeof COMPLIANCE_STATUS];

export interface StatusEvent {
  status: string;
  created_at: string;
}

export interface StatusCertificate {
  model_version: string;
  created_at: string | null;
  verification: string;
  regulation_versions: { version_id: string }[];
}

export interface DerivedStatus {
  status: ComplianceStatus;
  headline: string;
  detail: string;
}

export interface StatusInput {
  /** CI gate events, newest first. */
  events: StatusEvent[];
  /** Certificates, newest first. */
  certificates: StatusCertificate[];
  /** Version ids of the rules active right now. */
  activeVersionIds: string[];
}

function time(iso: string | null): number {
  return iso ? Date.parse(iso) : 0;
}

/** Plain-English compliance status for the compliance officer. No rule IDs,
 * no technical terms. */
export function deriveComplianceStatus(input: StatusInput): DerivedStatus {
  const latestCert = input.certificates.find((c) => c.verification === 'valid');
  const latestEvent = input.events[0];

  if (
    latestEvent?.status === GATE_STATUS.VIOLATION &&
    time(latestEvent.created_at) > time(latestCert?.created_at ?? null)
  ) {
    return {
      status: COMPLIANCE_STATUS.VIOLATION,
      headline: 'A new model did not pass a compliance check',
      detail:
        'It was blocked from deployment. The model already in use is not affected.',
    };
  }
  if (!latestCert) {
    return {
      status: COMPLIANCE_STATUS.UNKNOWN,
      headline: 'No model has been certified yet',
      detail: 'A certificate is issued when a model passes every compliance check.',
    };
  }
  const covered = new Set(latestCert.regulation_versions.map((r) => r.version_id));
  const uncovered = input.activeVersionIds.filter((id) => !covered.has(id));
  if (input.activeVersionIds.length === 0 || uncovered.length > 0) {
    return {
      status: COMPLIANCE_STATUS.PENDING,
      headline: 'The rules have changed since the last certified model',
      detail: 'A new model must pass the checks against the current rules.',
    };
  }
  return {
    status: COMPLIANCE_STATUS.COMPLIANT,
    headline: `The current model meets all ${input.activeVersionIds.length} active rules`,
    detail: `Certified model: ${latestCert.model_version}.`,
  };
}
