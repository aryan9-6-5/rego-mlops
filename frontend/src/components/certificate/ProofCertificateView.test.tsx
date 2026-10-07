import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { makeCertificate } from '@/test/fixtures';
import { ProofCertificateView } from './ProofCertificateView';

const downloadCertificate = vi.fn();
vi.mock('@/lib/api/certificates', () => ({
  downloadCertificate: (c: unknown) => downloadCertificate(c),
}));

const cert = makeCertificate();

afterEach(() => {
  vi.restoreAllMocks();
  downloadCertificate.mockReset();
});

describe('ProofCertificateView', () => {
  it('shows the model AND the regulation version, in words, for a compliance officer', () => {
    render(<ProofCertificateView certificate={cert} technicalView={false} />);
    expect(screen.getByText('v2.1.4')).toBeInTheDocument();
    expect(screen.getByText('RBI section 4.1, version of 7 Oct 2026')).toBeInTheDocument();
  });

  it('keeps the proof hash, rule ids and Z3 wording off the compliance officer screen', () => {
    const { container } = render(<ProofCertificateView certificate={cert} technicalView={false} />);
    expect(container.textContent).not.toContain(cert.proof_hash);
    expect(container.textContent).not.toMatch(/Z3|RBI-4\.1-2026/);
    expect(screen.getByText(/Checked automatically against every active rule/)).toBeInTheDocument();
  });

  it('shows the full hash, version id and Z3 footer to the ML engineer', () => {
    const { container } = render(<ProofCertificateView certificate={cert} technicalView />);
    expect(container.textContent).toContain(cert.proof_hash);
    expect(screen.getByText('RBI-4.1-20261007T120000000001Z')).toBeInTheDocument();
    expect(screen.getByText(/Verified by Z3 SMT Solver/)).toBeInTheDocument();
  });

  it('copies the hash even when it is not shown', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('navigator', { clipboard: { writeText } });
    render(<ProofCertificateView certificate={cert} technicalView={false} />);
    fireEvent.click(screen.getByRole('button', { name: 'Copy hash' }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(cert.proof_hash));
    expect(await screen.findByText('Hash copied')).toBeInTheDocument();
  });

  it('says so, instead of failing silently, when the clipboard is blocked', async () => {
    vi.stubGlobal('navigator', {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error('denied')) },
    });
    render(<ProofCertificateView certificate={cert} technicalView={false} />);
    fireEvent.click(screen.getByRole('button', { name: 'Copy hash' }));
    expect(await screen.findByText(/Could not copy/)).toBeInTheDocument();
  });

  it('downloads the whole certificate', () => {
    render(<ProofCertificateView certificate={cert} technicalView={false} />);
    fireEvent.click(screen.getByRole('button', { name: 'Download certificate' }));
    expect(downloadCertificate).toHaveBeenCalledWith(cert);
  });

  it('copes with a missing issue date', () => {
    render(
      <ProofCertificateView certificate={makeCertificate({ created_at: null })} technicalView={false} />,
    );
    expect(screen.getByText(/Unknown date/)).toBeInTheDocument();
  });
});
