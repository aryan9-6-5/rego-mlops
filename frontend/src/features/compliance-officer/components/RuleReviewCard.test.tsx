import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { makeRegulation } from '@/test/fixtures';
import { RuleReviewCard } from './RuleReviewCard';

const approve = vi.fn();
const reject = vi.fn();
let approveState: { isPending: boolean; error: unknown } = { isPending: false, error: null };

vi.mock('../api/regulations', () => ({
  useApproveRegulation: () => ({ mutate: approve, ...approveState }),
  useRejectRegulation: () => ({ mutate: reject, isPending: false, error: null }),
}));

beforeEach(() => {
  approve.mockReset();
  reject.mockReset();
  approveState = { isPending: false, error: null };
});

describe('RuleReviewCard', () => {
  it('shows the source text beside a plain-English meaning', () => {
    render(<RuleReviewCard regulation={makeRegulation()} onDone={() => {}} />);
    expect(screen.getByText('Lending models shall not use PIN codes.')).toBeInTheDocument();
    expect(screen.getByText('Models must not use PIN codes.')).toBeInTheDocument();
  });

  it('shows the exact condition in words and no raw logic or rule id', () => {
    const { container } = render(<RuleReviewCard regulation={makeRegulation()} onDone={() => {}} />);
    expect(screen.getByText('The weight of pin code equals 0.')).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/declare-const|assert|RBI-4\.1|z3/i);
    expect(screen.getByText(/RBI section 4\.1, version of 7 Oct 2026/)).toBeInTheDocument();
  });

  it('refuses to show logic it cannot translate', () => {
    render(
      <RuleReviewCard
        regulation={makeRegulation({ formal_logic: '(assert (forall ((x Int)) (> x 0)))' })}
        onDone={() => {}}
      />,
    );
    expect(screen.getByText(/cannot be shown in plain words/)).toBeInTheDocument();
  });

  it('needs two deliberate actions to approve', () => {
    render(<RuleReviewCard regulation={makeRegulation()} onDone={() => {}} />);
    expect(screen.queryByRole('button', { name: 'Activate rule' })).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: 'Yes, approve rule' }));
    expect(approve).not.toHaveBeenCalled(); // the first click only opens the confirmation

    const activate = screen.getByRole('button', { name: 'Activate rule' });
    expect(activate).toBeDisabled();
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'activate' } });
    expect(activate).toBeDisabled(); // case matters
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'ACTIVATE' } });
    expect(activate).toBeEnabled();

    fireEvent.click(activate);
    expect(approve).toHaveBeenCalledTimes(1);
    expect(approve.mock.calls[0][0]).toBe('reg-1');
  });

  it('warns what activation means before it can be confirmed', () => {
    render(<RuleReviewCard regulation={makeRegulation()} onDone={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: 'Yes, approve rule' }));
    expect(screen.getByText(/deployment will be blocked/)).toBeInTheDocument();
  });

  it('can go back from the confirmation without approving', () => {
    render(<RuleReviewCard regulation={makeRegulation()} onDone={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: 'Yes, approve rule' }));
    fireEvent.click(screen.getByRole('button', { name: 'Go back' }));
    expect(screen.getByRole('button', { name: 'Yes, approve rule' })).toBeInTheDocument();
    expect(approve).not.toHaveBeenCalled();
  });

  it('needs a confirmation to reject and sends the reason', () => {
    render(<RuleReviewCard regulation={makeRegulation()} onDone={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: 'No, reject rule' }));
    expect(reject).not.toHaveBeenCalled();
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'wrong intent' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirm rejection' }));
    expect(reject.mock.calls[0][0]).toEqual({ id: 'reg-1', reason: 'wrong intent' });
  });

  it('says what is happening while activating', () => {
    approveState = { isPending: true, error: null };
    render(<RuleReviewCard regulation={makeRegulation()} onDone={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: 'Yes, approve rule' }));
    expect(screen.getByText('Activating rule and updating knowledge graph...')).toBeInTheDocument();
  });

  it('shows a failure inline and keeps the card open', () => {
    approveState = { isPending: false, error: new Error('network') };
    render(<RuleReviewCard regulation={makeRegulation()} onDone={() => {}} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Yes, approve rule' })).toBeInTheDocument();
  });
});
