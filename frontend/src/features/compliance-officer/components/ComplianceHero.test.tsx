import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { COMPLIANCE_STATUS, type ComplianceStatus } from '@/lib/status/complianceStatus';
import { ComplianceHero } from './ComplianceHero';

const STATUSES = Object.values(COMPLIANCE_STATUS) as ComplianceStatus[];

function hero(status: ComplianceStatus, live = true) {
  return render(
    <ComplianceHero status={status} headline="Headline text" detail="Detail text" live={live} />,
  );
}

describe('ComplianceHero', () => {
  it.each([
    [COMPLIANCE_STATUS.COMPLIANT, 'Compliant'],
    [COMPLIANCE_STATUS.VIOLATION, 'Violation'],
    [COMPLIANCE_STATUS.PENDING, 'Needs attention'],
    [COMPLIANCE_STATUS.UNKNOWN, 'Not yet certified'],
  ])('shows the word "%s" as "%s", not just a colour', (status, label) => {
    hero(status);
    expect(screen.getByRole('status')).toHaveTextContent(label);
  });

  it('shows the headline and detail for every status', () => {
    for (const status of STATUSES) {
      const { unmount } = hero(status);
      expect(screen.getByText('Headline text')).toBeInTheDocument();
      expect(screen.getByText('Detail text')).toBeInTheDocument();
      unmount();
    }
  });

  it('pulses the dot on a violation only', () => {
    const { container, unmount } = hero(COMPLIANCE_STATUS.VIOLATION);
    expect(container.querySelector('.animate-pulse')).not.toBeNull();
    unmount();
    const calm = hero(COMPLIANCE_STATUS.COMPLIANT);
    expect(calm.container.querySelector('.animate-pulse')).toBeNull();
  });

  it('is a polite live region so a change is announced without a refresh', () => {
    hero(COMPLIANCE_STATUS.COMPLIANT);
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  });

  it('says when the live feed is down', () => {
    hero(COMPLIANCE_STATUS.COMPLIANT, false);
    expect(screen.getByText('Reconnecting...')).toBeInTheDocument();
  });
});
