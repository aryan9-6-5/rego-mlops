import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Link } from 'react-router-dom';
import { errorMessage } from '@/lib/api/client';
import { JOB_STATUS } from '@/lib/utils/constants';
import { useCreateRegulation, useRegulationJob } from '../api/regulations';
import {
  validateRegulationForm,
  type RegulationFormErrors,
} from '../lib/validateRegulationForm';

const FIELD = 'w-full rounded-lg border bg-slate-950 px-4 py-3 text-white';

const RegulationUpload: React.FC = () => {
  const [section, setSection] = useState('');
  const [content, setContent] = useState('');
  const [errors, setErrors] = useState<RegulationFormErrors>({});
  const [jobId, setJobId] = useState<string | null>(null);
  const create = useCreateRegulation();
  const job = useRegulationJob(jobId);

  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0];
    if (file) setContent(await file.text());
  }, []);
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/plain': ['.txt', '.md'] },
    multiple: false,
    noClick: true,
  });

  const reset = () => {
    setJobId(null);
    create.reset();
  };

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const found = validateRegulationForm(section, content);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    create.mutate(
      { section: section.trim(), content },
      { onSuccess: (data) => setJobId(data.job_id) },
    );
  };

  const failureMessage =
    job.data?.status === JOB_STATUS.FAILED
      ? (job.data.error ?? 'Rule extraction failed.')
      : job.isError
        ? errorMessage(job.error)
        : null;

  if (jobId && job.data?.status === JOB_STATUS.COMPLETE) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 rounded-2xl border border-emerald-800 bg-emerald-950/30 p-8">
        <h2 className="text-xl font-semibold text-white">Rules extracted</h2>
        <p className="text-slate-200">They are ready for your review.</p>
        <div className="flex gap-4">
          <Link to="/approval-queue" className="rounded-lg bg-blue-600 px-5 py-3 font-medium text-white hover:bg-blue-500">
            Go to approval queue
          </Link>
          <button type="button" onClick={reset} className="px-4 text-slate-300 hover:text-white">
            Add another regulation
          </button>
        </div>
      </div>
    );
  }

  if (jobId && !failureMessage) {
    return (
      <div role="status" className="mx-auto max-w-3xl space-y-2 rounded-2xl border border-slate-800 bg-slate-900/50 p-8">
        <h2 className="text-xl font-semibold text-white">Extracting rules...</h2>
        <p className="text-slate-300">
          Sending your text to the AI, then checking the logical structure of each
          rule. This usually takes 10 to 30 seconds.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} noValidate className="mx-auto max-w-3xl space-y-6 text-base">
      {failureMessage && (
        <p role="alert" className="rounded-lg border border-red-800 bg-red-950 p-4 text-red-200">
          {failureMessage}
        </p>
      )}
      {create.isError && (
        <p role="alert" className="rounded-lg border border-red-800 bg-red-950 p-4 text-red-200">
          {errorMessage(create.error)}
        </p>
      )}

      <label className="block">
        <span className="mb-2 block font-medium text-slate-200">Section</span>
        <input
          value={section}
          onChange={(e) => setSection(e.target.value)}
          placeholder="4.1"
          aria-invalid={errors.section !== undefined}
          className={`${FIELD} ${errors.section ? 'border-red-600' : 'border-slate-700'}`}
        />
        {errors.section && <span role="alert" className="mt-1 block text-sm text-red-300">{errors.section}</span>}
      </label>

      <div {...getRootProps()}>
        <label htmlFor="regulation-text" className="mb-2 block font-medium text-slate-200">
          Regulatory text
        </label>
        <input {...getInputProps()} />
        <textarea
          id="regulation-text"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Paste regulatory text here, or drop a .txt file..."
          aria-invalid={errors.content !== undefined}
          className={`${FIELD} min-h-[200px] border-2 border-dashed font-mono text-sm ${
            errors.content ? 'border-red-600' : isDragActive ? 'border-blue-500' : 'border-slate-700'
          }`}
        />
        {errors.content && <span role="alert" className="mt-1 block text-sm text-red-300">{errors.content}</span>}
      </div>

      <button
        type="submit"
        disabled={create.isPending}
        className="h-12 rounded-lg bg-blue-600 px-6 font-medium text-white enabled:hover:bg-blue-500 disabled:opacity-40"
      >
        {create.isPending ? 'Sending to the AI...' : 'Extract rules'}
      </button>
    </form>
  );
};

export default RegulationUpload;
