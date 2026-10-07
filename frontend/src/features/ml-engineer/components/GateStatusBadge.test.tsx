import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { GATE_STATUS, type GateStatus } from '@/lib/utils/constants';
import { GateStatusBadge } from './GateStatusBadge';

describe('GateStatusBadge', () => {
  it.each([
    [GATE_STATUS.QUEUED, 'Queued'],
    [GATE_STATUS.RUNNING, 'Running'],
    [GATE_STATUS.COMPLIANT, 'Compliant'],
    [GATE_STATUS.VIOLATION, 'Violation'],
    [GATE_STATUS.SKIPPED, 'Skipped'],
  ] as [GateStatus, string][])('shows %s with the text "%s"', (status, label) => {
    const { container } = render(<GateStatusBadge status={status} />);
    expect(container).toHaveTextContent(label);
  });

  it('pulses for running and violation so they are noticed', () => {
    for (const status of [GATE_STATUS.RUNNING, GATE_STATUS.VIOLATION]) {
      const { container, unmount } = render(<GateStatusBadge status={status} />);
      expect(container.querySelector('.animate-pulse')).not.toBeNull();
      unmount();
    }
  });
});
