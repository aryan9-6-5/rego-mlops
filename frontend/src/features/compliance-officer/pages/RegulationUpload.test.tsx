import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MAX_REGULATORY_TEXT_CHARS } from '@/lib/utils/constants';
import RegulationUpload from './RegulationUpload';

const mutate = vi.fn();
let create: { mutate: typeof mutate; isPending: boolean; isError: boolean; error: unknown; reset: () => void };
let job: { data?: { status: string; error: string | null }; isError: boolean; error: unknown };

vi.mock('../api/regulations', () => ({
  useCreateRegulation: () => create,
  useRegulationJob: () => job,
}));

function setup() {
  return render(
    <MemoryRouter>
      <RegulationUpload />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mutate.mockReset();
  create = { mutate, isPending: false, isError: false, error: null, reset: vi.fn() };
  job = { data: undefined, isError: false, error: null };
});

describe('RegulationUpload', () => {
  it('shows inline errors next to both fields and sends nothing when empty', () => {
    setup();
    fireEvent.click(screen.getByRole('button', { name: 'Extract rules' }));
    const alerts = screen.getAllByRole('alert').map((a) => a.textContent);
    expect(alerts).toHaveLength(2);
    expect(alerts.join(' ')).toMatch(/section/i);
    expect(alerts.join(' ')).toMatch(/Paste the regulatory text/);
    expect(mutate).not.toHaveBeenCalled();
  });

  it('rejects text over the limit with the actual numbers', () => {
    setup();
    fireEvent.change(screen.getByPlaceholderText('4.1'), { target: { value: '4.1' } });
    fireEvent.change(screen.getByLabelText('Regulatory text'), {
      target: { value: 'x'.repeat(MAX_REGULATORY_TEXT_CHARS + 1) },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Extract rules' }));
    expect(screen.getByRole('alert')).toHaveTextContent(/50,001 characters.*50,000/);
    expect(mutate).not.toHaveBeenCalled();
  });

  it('sends the trimmed section and the text when valid', () => {
    setup();
    fireEvent.change(screen.getByPlaceholderText('4.1'), { target: { value: ' 4.1 ' } });
    fireEvent.change(screen.getByLabelText('Regulatory text'), {
      target: { value: 'Models shall not use PIN codes.' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Extract rules' }));
    expect(mutate).toHaveBeenCalledTimes(1);
    expect(mutate.mock.calls[0][0]).toEqual({
      section: '4.1',
      content: 'Models shall not use PIN codes.',
    });
  });

  it('says what is happening while the request is sent', () => {
    create = { ...create, isPending: true };
    setup();
    expect(screen.getByRole('button', { name: 'Sending to the AI...' })).toBeDisabled();
  });

  it('shows a request failure inline', () => {
    create = { ...create, isError: true, error: new Error('x') };
    setup();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});

describe('RegulationUpload while the job runs', () => {
  const startedForm = () => {
    // The form moves to the progress screen once a job id exists. Drive it through submit.
    mutate.mockImplementation((_body: unknown, options: { onSuccess: (d: { job_id: string }) => void }) =>
      options.onSuccess({ job_id: 'job-1' }),
    );
    setup();
    fireEvent.change(screen.getByPlaceholderText('4.1'), { target: { value: '4.1' } });
    fireEvent.change(screen.getByLabelText('Regulatory text'), { target: { value: 'text' } });
    fireEvent.click(screen.getByRole('button', { name: 'Extract rules' }));
  };

  it('shows a progress message that says what it is doing', () => {
    job = { data: { status: 'running', error: null }, isError: false, error: null };
    startedForm();
    expect(screen.getByRole('status')).toHaveTextContent(/10 to 30 seconds/);
  });

  it('points to the approval queue when extraction finishes', () => {
    job = { data: { status: 'complete', error: null }, isError: false, error: null };
    startedForm();
    expect(screen.getByRole('link', { name: 'Go to approval queue' })).toHaveAttribute('href', '/approval-queue');
  });

  it('shows an LLM failure inline and lets the officer try again', () => {
    job = {
      data: { status: 'failed', error: 'Rule extraction failed. Please try again.' },
      isError: false,
      error: null,
    };
    startedForm();
    expect(screen.getByRole('alert')).toHaveTextContent('Rule extraction failed. Please try again.');
    expect(screen.getByRole('button', { name: 'Extract rules' })).toBeInTheDocument();
  });
});
