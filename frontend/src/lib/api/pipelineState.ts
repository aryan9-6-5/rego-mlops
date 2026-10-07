import { GATE_STATUS, type GateName, type GateStatus } from '@/lib/utils/constants';

export interface Violation {
  rule_id: string;
  plain_english: string;
  counterexample: Record<string, string>;
}

export interface GateEvent {
  gate: GateName;
  status: GateStatus;
  model_version: string;
  rule_ids: string[];
  duration_ms: number;
  plain_english: string;
  violations: Violation[];
  timestamp: string;
}

export interface PipelineRun {
  model_version: string;
  status: GateStatus;
  gates: GateEvent[];
}

export function runStatus(gates: GateEvent[]): GateStatus {
  if (gates.some((g) => g.status === GATE_STATUS.VIOLATION)) return GATE_STATUS.VIOLATION;
  if (gates.every((g) => g.status === GATE_STATUS.COMPLIANT)) return GATE_STATUS.COMPLIANT;
  return GATE_STATUS.RUNNING;
}

/** Merge a streamed gate event into the current run. Returns null when the
 * event belongs to a different model, so the caller should refetch. */
export function applyGateEvent(run: PipelineRun, event: GateEvent): PipelineRun | null {
  if (run.model_version !== event.model_version) return null;
  const gates = run.gates.map((g) => (g.gate === event.gate ? event : g));
  return { ...run, gates, status: runStatus(gates) };
}

export function isGateEvent(value: unknown): value is GateEvent {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.gate === 'string' &&
    typeof v.status === 'string' &&
    typeof v.model_version === 'string' &&
    Array.isArray(v.violations)
  );
}
