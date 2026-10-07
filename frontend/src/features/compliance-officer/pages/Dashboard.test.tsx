import { act, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Certificate } from '@/lib/api/certificateHelpers';
import { usePipelineEventsStore, type PipelineEventRow } from '@/lib/realtime/pipelineEvents';
import { makeCertificate, makeRegulation } from '@/test/fixtures';
import type { Regulation } from '../api/regulations';
import Dashboard from './Dashboard';

type Query<T> = { data?: T; isLoading: boolean; isError: boolean; error: unknown };
let regulations: Query<Regulation[]>;
let certificates: Query<Certificate[]>;

vi.mock('../api/regulations', () => ({ useRegulations: () => regulations }));
vi.mock('@/lib/api/certificates', () => ({
  useCertificates: () => certificates,
  downloadCertificate: vi.fn(),
}));
vi.mock('@/lib/auth/useAuth', () => ({ useAuth: () => ({ role: 'compliance_officer' }) }));
vi.mock('@/lib/auth/supabase', () => ({ supabase: {} }));
vi.mock('@/lib/realtime/pipelineEvents', async (original) => {
  const actual = await original<typeof import('@/lib/realtime/pipelineEvents')>();
  return { ...actual, usePipelineEventsFeed: () => undefined };
});

const ACTIVE = makeRegulation({ id: 'a', status: 'active', version: '20261007T120000000001Z' });
const CERT = makeCertificate({ created_at: '2026-10-07T12:00:00Z' });

function event(id: string, status: string, at: string): PipelineEventRow {
  return {
    id,
    stage: 'ci',
    gate_name: 'symbolic_check',
    status,
    model_version: 'v3',
    rule_ids: [],
    duration_ms: 5,
    plain_english_result: 'x',
    created_at: at,
  };
}

const ok = <T,>(data: T): Query<T> => ({ data, isLoading: false, isError: false, error: null });

beforeEach(() => {
  regulations = ok([ACTIVE]);
  certificates = ok([CERT]);
  usePipelineEventsStore.setState({ events: [], loaded: true, error: null, live: true });
});

const setup = () =>
  render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );

describe('CO Dashboard', () => {
  it('shows the status while loading, in words', () => {
    usePipelineEventsStore.setState({ loaded: false });
    setup();
    expect(screen.getByText('Checking your current compliance status...')).toBeInTheDocument();
  });

  it('is green and plain when the latest certificate covers every rule in force', () => {
    setup();
    const hero = screen.getByRole('status');
    expect(hero).toHaveTextContent('Compliant');
    expect(hero).toHaveTextContent('The current model meets all 1 active rules');
  });

  it('turns red the moment a violation event arrives, with no page refresh', () => {
    setup();
    expect(screen.getByRole('status')).toHaveTextContent('Compliant');
    act(() => {
      usePipelineEventsStore.getState().addEvent(event('e1', 'violation', '2026-10-07T13:00:00Z'));
    });
    expect(screen.getByRole('status')).toHaveTextContent('Violation');
    expect(screen.getByText('A new model did not pass a compliance check')).toBeInTheDocument();
  });

  it('keeps technical detail out of the status text', () => {
    setup();
    act(() => {
      usePipelineEventsStore.getState().addEvent(event('e1', 'violation', '2026-10-07T13:00:00Z'));
    });
    expect(screen.getByRole('status').textContent).not.toMatch(/z3|RBI-|hash|SAT/i);
  });

  it('asks for attention when a new rule is not covered by any certificate', () => {
    regulations = ok([ACTIVE, makeRegulation({ id: 'b', status: 'active', rule_id: 'RBI-4.2', version: '2' })]);
    setup();
    expect(screen.getByRole('status')).toHaveTextContent('Needs attention');
  });

  it('counts the rules waiting for review and links to them', () => {
    regulations = ok([ACTIVE, makeRegulation({ id: 'p', status: 'pending_approval' })]);
    setup();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText(/rule is waiting for your review/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Review now' })).toHaveAttribute('href', '/approval-queue');
  });

  it('lists the rules in force with their plain summaries', () => {
    setup();
    expect(screen.getByText('Models must not use PIN codes.')).toBeInTheDocument();
  });

  it('shows an error per section instead of failing the whole page', () => {
    regulations = { data: undefined, isLoading: false, isError: true, error: new Error('x') };
    setup();
    expect(screen.getAllByRole('alert').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Recent certificates')).toBeInTheDocument();
  });

  it('has an empty state for certificates', () => {
    certificates = ok([]);
    setup();
    expect(screen.getByText(/No certificates yet/)).toBeInTheDocument();
  });
});
