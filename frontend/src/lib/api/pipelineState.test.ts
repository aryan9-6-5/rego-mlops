import { describe, expect, it } from 'vitest';
import { GATE_NAME, GATE_STATUS, type GateStatus } from '@/lib/utils/constants';
import {
  applyGateEvent,
  isGateEvent,
  type GateEvent,
  type PipelineRun,
} from './pipelineState';

function gate(name: GateEvent['gate'], status: GateStatus, model = 'v1'): GateEvent {
  return {
    gate: name,
    status,
    model_version: model,
    rule_ids: [],
    duration_ms: 0,
    plain_english: '',
    violations: [],
    timestamp: '2026-10-07T00:00:00Z',
  };
}

const run: PipelineRun = {
  model_version: 'v1',
  status: GATE_STATUS.RUNNING,
  gates: Object.values(GATE_NAME).map((n) => gate(n, GATE_STATUS.QUEUED)),
};

describe('applyGateEvent', () => {
  it('replaces the matching gate', () => {
    const next = applyGateEvent(run, gate(GATE_NAME.SYMBOLIC_CHECK, GATE_STATUS.RUNNING));
    expect(next?.gates[0].status).toBe(GATE_STATUS.RUNNING);
    expect(next?.status).toBe(GATE_STATUS.RUNNING);
  });

  it('marks the run as a violation when any gate fails', () => {
    const next = applyGateEvent(run, gate(GATE_NAME.SYMBOLIC_CHECK, GATE_STATUS.VIOLATION));
    expect(next?.status).toBe(GATE_STATUS.VIOLATION);
  });

  it('marks the run compliant only when every gate is compliant', () => {
    const done = {
      ...run,
      gates: run.gates.map((g) => ({ ...g, status: GATE_STATUS.COMPLIANT })),
    };
    expect(applyGateEvent(done, done.gates[0])?.status).toBe(GATE_STATUS.COMPLIANT);
  });

  it('asks for a refetch when the event is for another model', () => {
    expect(applyGateEvent(run, gate(GATE_NAME.REGRESSION, GATE_STATUS.RUNNING, 'v2'))).toBeNull();
  });
});

describe('isGateEvent', () => {
  it('accepts events and rejects junk', () => {
    expect(isGateEvent(gate(GATE_NAME.REGRESSION, GATE_STATUS.QUEUED))).toBe(true);
    expect(isGateEvent(null)).toBe(false);
    expect(isGateEvent({ gate: 'x' })).toBe(false);
  });
});
