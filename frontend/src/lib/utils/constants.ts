export const REGULATION_STATUS = {
  EXTRACTED: 'extracted',
  Z3_VALIDATED: 'z3_validated',
  Z3_REJECTED: 'z3_rejected',
  PENDING_APPROVAL: 'pending_approval',
  APPROVED: 'approved',
  REJECTED: 'rejected',
  ACTIVE: 'active',
} as const;

export type RegulationStatus =
  (typeof REGULATION_STATUS)[keyof typeof REGULATION_STATUS];

export const JOB_STATUS = {
  RUNNING: 'running',
  COMPLETE: 'complete',
  FAILED: 'failed',
} as const;

export type JobStatus = (typeof JOB_STATUS)[keyof typeof JOB_STATUS];

export const MAX_REGULATORY_TEXT_CHARS = 50_000;
export const ACTIVATE_CONFIRMATION_WORD = 'ACTIVATE';
export const JOB_POLL_INTERVAL_MS = 2000;
