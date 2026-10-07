import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { REGULATION_STATUS, type RegulationStatus } from '@/lib/utils/constants';
import { StatusBadge } from './ComplianceBadge';

const ALL = Object.values(REGULATION_STATUS) as RegulationStatus[];

describe('StatusBadge', () => {
  it('renders every status without throwing', () => {
    for (const status of ALL) {
      expect(() => render(<StatusBadge status={status} />)).not.toThrow();
    }
  });

  it('always shows a text label next to the colour', () => {
    for (const status of ALL) {
      const { container, unmount } = render(<StatusBadge status={status} />);
      const text = container.textContent ?? '';
      expect(text.trim().length).toBeGreaterThan(2);
      expect(container.querySelector('[aria-hidden="true"]')).not.toBeNull();
      unmount();
    }
  });

  it.each([
    [REGULATION_STATUS.PENDING_APPROVAL, 'Pending Approval'],
    [REGULATION_STATUS.ACTIVE, 'Active'],
    [REGULATION_STATUS.REJECTED, 'Rejected'],
    [REGULATION_STATUS.Z3_REJECTED, 'Verification Failed'],
    [REGULATION_STATUS.SUPERSEDED, 'Superseded'],
  ])('labels %s as "%s"', (status, label) => {
    render(<StatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it('never shows technical status names to the compliance officer', () => {
    for (const status of ALL) {
      const { container, unmount } = render(<StatusBadge status={status} />);
      expect(container.textContent).not.toMatch(/z3|_/i);
      unmount();
    }
  });
});
