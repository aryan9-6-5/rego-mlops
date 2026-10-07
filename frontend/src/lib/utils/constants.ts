export const REGULATION_STATUS = {
  EXTRACTED: 'extracted',
  Z3_VALIDATED: 'z3_validated',
  Z3_REJECTED: 'z3_rejected',
  PENDING_APPROVAL: 'pending_approval',
  APPROVED: 'approved',
  REJECTED: 'rejected',
  ACTIVE: 'active',
  SUPERSEDED: 'superseded',
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

export const GATE_NAME = {
  SYMBOLIC_CHECK: 'symbolic_check',
  REG_ATTACK: 'reg_attack',
  FAIRNESS_CHECK: 'fairness_check',
  REGRESSION: 'regression',
} as const;

export type GateName = (typeof GATE_NAME)[keyof typeof GATE_NAME];

export const GATE_LABEL: Record<GateName, string> = {
  [GATE_NAME.SYMBOLIC_CHECK]: 'Symbolic check (Z3)',
  [GATE_NAME.REG_ATTACK]: 'Regulatory attack',
  [GATE_NAME.FAIRNESS_CHECK]: 'Fairness check',
  [GATE_NAME.REGRESSION]: 'Performance regression',
};

export const GATE_STATUS = {
  QUEUED: 'queued',
  RUNNING: 'running',
  COMPLIANT: 'compliant',
  VIOLATION: 'violation',
  SKIPPED: 'skipped',
} as const;

export type GateStatus = (typeof GATE_STATUS)[keyof typeof GATE_STATUS];
