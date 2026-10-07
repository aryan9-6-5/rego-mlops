import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Certificate } from '@/lib/api/certificateHelpers';
import { makeCertificate } from '@/test/fixtures';
import Certificates from './Certificates';

type Query = {
  data?: Certificate[];
  isLoading: boolean;
  isError: boolean;
  error: unknown;
};
let query: Query;

vi.mock('@/lib/api/certificates', () => ({
  useCertificates: () => query,
  downloadCertificate: vi.fn(),
}));

beforeEach(() => {
  query = { data: [], isLoading: false, isError: false, error: null };
});

describe('Certificates (compliance officer)', () => {
  it('says what it is loading', () => {
    query = { ...query, isLoading: true, data: undefined };
    render(<Certificates />);
    expect(screen.getByText('Loading certificates...')).toBeInTheDocument();
  });

  it('shows an inline error, not a blank screen', () => {
    query = { ...query, isError: true, error: new Error('x'), data: undefined };
    render(<Certificates />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('explains an empty list', () => {
    render(<Certificates />);
    expect(screen.getByText(/No certificates have been issued yet/)).toBeInTheDocument();
  });

  it('lists intact certificates with a download button and no hash on screen', () => {
    query = { ...query, data: [makeCertificate()] };
    const { container } = render(<Certificates />);
    expect(screen.getByRole('button', { name: 'Download certificate' })).toBeInTheDocument();
    expect(container.textContent).not.toContain(makeCertificate().proof_hash);
  });

  it('shows a tampered certificate as failed and offers no way to use it', () => {
    query = {
      ...query,
      data: [
        makeCertificate({
          verification: 'tampered',
          proof_hash: '',
          hmac_signature: '',
          regulation_versions: [],
        }),
      ],
    };
    render(<Certificates />);
    expect(screen.getByRole('alert')).toHaveTextContent(/Verification failed/);
    expect(screen.queryByRole('button', { name: /Download|Copy/ })).toBeNull();
  });

  it('shows good and tampered certificates side by side', () => {
    query = {
      ...query,
      data: [
        makeCertificate({ id: 'a', model_version: 'v2' }),
        makeCertificate({ id: 'b', model_version: 'v1', verification: 'tampered', regulation_versions: [] }),
      ],
    };
    render(<Certificates />);
    expect(screen.getAllByRole('button', { name: 'Download certificate' })).toHaveLength(1);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});
