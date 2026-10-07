import { describe, expect, it } from 'vitest';
import {
  COMPLIANCE_STATUS,
  deriveComplianceStatus,
  type StatusCertificate,
  type StatusEvent,
} from './complianceStatus';

const cert: StatusCertificate = {
  model_version: 'v1',
  created_at: '2026-10-07T10:00:00Z',
  verification: 'valid',
  regulation_versions: [{ version_id: 'RBI-4.1-a' }],
};

function event(status: string, at: string): StatusEvent {
  return { status, created_at: at };
}

describe('deriveComplianceStatus', () => {
  it('is compliant when the latest certificate covers every active rule', () => {
    const result = deriveComplianceStatus({
      events: [event('compliant', '2026-10-07T09:00:00Z')],
      certificates: [cert],
      activeVersionIds: ['RBI-4.1-a'],
    });
    expect(result.status).toBe(COMPLIANCE_STATUS.COMPLIANT);
  });

  it('turns to violation when a newer gate fails', () => {
    const result = deriveComplianceStatus({
      events: [event('violation', '2026-10-07T11:00:00Z')],
      certificates: [cert],
      activeVersionIds: ['RBI-4.1-a'],
    });
    expect(result.status).toBe(COMPLIANCE_STATUS.VIOLATION);
  });

  it('ignores a violation older than the latest certificate', () => {
    const result = deriveComplianceStatus({
      events: [event('violation', '2026-10-07T09:00:00Z')],
      certificates: [cert],
      activeVersionIds: ['RBI-4.1-a'],
    });
    expect(result.status).toBe(COMPLIANCE_STATUS.COMPLIANT);
  });

  it('is pending when a new rule is not covered by the certificate', () => {
    const result = deriveComplianceStatus({
      events: [],
      certificates: [cert],
      activeVersionIds: ['RBI-4.1-a', 'RBI-4.2-b'],
    });
    expect(result.status).toBe(COMPLIANCE_STATUS.PENDING);
  });

  it('is unknown with no certificate', () => {
    const result = deriveComplianceStatus({
      events: [],
      certificates: [],
      activeVersionIds: ['RBI-4.1-a'],
    });
    expect(result.status).toBe(COMPLIANCE_STATUS.UNKNOWN);
  });

  it('does not trust a tampered certificate', () => {
    const result = deriveComplianceStatus({
      events: [],
      certificates: [{ ...cert, verification: 'tampered' }],
      activeVersionIds: ['RBI-4.1-a'],
    });
    expect(result.status).toBe(COMPLIANCE_STATUS.UNKNOWN);
  });

  it('never puts rule ids or technical terms in the text', () => {
    const text = JSON.stringify(
      deriveComplianceStatus({
        events: [event('violation', '2026-10-07T11:00:00Z')],
        certificates: [cert],
        activeVersionIds: ['RBI-4.1-a'],
      }),
    );
    expect(text).not.toMatch(/RBI-|Z3|SAT|hash/i);
  });
});
