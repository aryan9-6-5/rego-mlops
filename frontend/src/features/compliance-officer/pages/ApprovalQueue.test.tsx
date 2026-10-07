import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { makeRegulation } from '@/test/fixtures';
import type { Regulation } from '../api/regulations';
import ApprovalQueue from './ApprovalQueue';

type Query = { data?: Regulation[]; isLoading: boolean; isError: boolean; error: unknown };
let query: Query;

vi.mock('../api/regulations', () => ({
  useRegulations: () => query,
  useApproveRegulation: () => ({ mutate: vi.fn(), isPending: false, error: null }),
  useRejectRegulation: () => ({ mutate: vi.fn(), isPending: false, error: null }),
}));

const setup = () =>
  render(
    <MemoryRouter>
      <ApprovalQueue />
    </MemoryRouter>,
  );

beforeEach(() => {
  query = { data: [], isLoading: false, isError: false, error: null };
});

describe('ApprovalQueue', () => {
  it('says what it is loading', () => {
    query = { ...query, isLoading: true, data: undefined };
    setup();
    expect(screen.getByText(/Loading rules awaiting your review/)).toBeInTheDocument();
  });

  it('shows an inline error', () => {
    query = { ...query, isError: true, error: new Error('x'), data: undefined };
    setup();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('explains an empty queue and links to adding a regulation', () => {
    setup();
    expect(screen.getByText(/No rules are waiting for review/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Add a regulation' })).toHaveAttribute('href', '/regulations');
  });

  it('lists pending rules with plain labels and no rule ids', () => {
    query = { ...query, data: [makeRegulation()] };
    const { container } = setup();
    expect(screen.getByText('Models must not use PIN codes.')).toBeInTheDocument();
    expect(screen.getByText(/RBI section 4\.1, version of 7 Oct 2026/)).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/RBI-4\.1/);
  });

  it('opens one rule at a time and can return to the queue', () => {
    query = { ...query, data: [makeRegulation(), makeRegulation({ id: 'reg-2', description: 'Second rule.' })] };
    setup();
    fireEvent.click(screen.getByText('Models must not use PIN codes.'));
    expect(screen.getByText('Review this rule')).toBeInTheDocument();
    expect(screen.queryByText('Second rule.')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /Back to queue/ }));
    expect(screen.getByText('Second rule.')).toBeInTheDocument();
  });

  it('shows rules that failed verification in plain English, never the raw reason code', () => {
    query = {
      ...query,
      data: [
        makeRegulation({
          id: 'bad',
          status: 'z3_rejected',
          validation_message: 'The rule is always true, so it would not restrict anything.',
        }),
      ],
    };
    const { container } = setup();
    expect(screen.getByText('Could not be verified')).toBeInTheDocument();
    expect(screen.getByText(/always true, so it would not restrict anything/)).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/z3_rejected/);
    expect(screen.getByText('Verification Failed')).toBeInTheDocument();
  });

  it('keeps active rules in a separate list that cannot be approved again', () => {
    query = { ...query, data: [makeRegulation({ status: 'active' })] };
    setup();
    expect(screen.getByText('Active rules')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /approve/i })).toBeNull();
  });
});
