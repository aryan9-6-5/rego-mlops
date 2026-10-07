import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ModelDiff as Diff } from '@/lib/api/insights';
import ModelDiff from './ModelDiff';

type Query = { data?: Diff; isFetching: boolean; isError: boolean; error: unknown };
let diff: Query;
const requested: [string, string][] = [];

vi.mock('@/lib/api/insights', () => ({
  useModelDiff: (from: string, to: string) => {
    requested.push([from, to]);
    return diff;
  },
}));
vi.mock('@/lib/api/models', () => ({
  useModelLineages: () => ({ data: [{ model_version: 'v1' }, { model_version: 'v2' }] }),
}));

beforeEach(() => {
  requested.length = 0;
  diff = { data: undefined, isFetching: false, isError: false, error: null };
});

describe('ModelDiff', () => {
  it('invites the user to pick two versions', () => {
    render(<ModelDiff />);
    expect(screen.getByText(/Choose two model versions/)).toBeInTheDocument();
  });

  it('offers the known model versions', () => {
    const { container } = render(<ModelDiff />);
    expect(container.querySelectorAll('datalist option')).toHaveLength(2);
  });

  it('asks for the diff with the versions typed in', () => {
    render(<ModelDiff />);
    fireEvent.change(screen.getByLabelText('From version'), { target: { value: ' v1 ' } });
    fireEvent.change(screen.getByLabelText('To version'), { target: { value: 'v2' } });
    expect(requested.at(-1)).toEqual(['v1', 'v2']);
  });

  it('says what it is doing while comparing', () => {
    diff = { ...diff, isFetching: true };
    render(<ModelDiff />);
    expect(screen.getByRole('status')).toHaveTextContent(/Comparing the two models against the active rules/);
  });

  it('shows an inline error for an unknown version', () => {
    diff = { ...diff, isError: true, error: new Error('x') };
    render(<ModelDiff />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('says when nothing differs', () => {
    diff = { ...diff, data: { from_version: 'v1', to_version: 'v2', changes: [] } };
    render(<ModelDiff />);
    expect(screen.getByText(/use the same features with the same weights/)).toBeInTheDocument();
  });

  it('highlights a change that touches an active rule in red, with the rule named', () => {
    diff = {
      ...diff,
      data: {
        from_version: 'v1',
        to_version: 'v2',
        changes: [
          { feature: 'pin_code', kind: 'added', before: null, after: 0.3, affects_rules: ['RBI-4.1'] },
          { feature: 'income', kind: 'changed', before: 0.4, after: 0.5, affects_rules: [] },
          { feature: 'age', kind: 'removed', before: 0.2, after: null, affects_rules: [] },
        ],
      },
    };
    const { container } = render(<ModelDiff />);
    const rows = container.querySelectorAll('tbody tr');
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveClass('bg-red-950/30');
    expect(rows[0]).toHaveTextContent('Affects RBI-4.1');
    expect(rows[1]).not.toHaveClass('bg-red-950/30');
    expect(rows[1]).toHaveTextContent('No rule affected');
    expect(screen.getByText('Added')).toBeInTheDocument();
    expect(screen.getByText('Removed')).toBeInTheDocument();
    expect(screen.getByText('Re-weighted')).toBeInTheDocument();
  });
});
