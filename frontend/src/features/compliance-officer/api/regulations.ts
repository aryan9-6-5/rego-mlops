import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import {
  JOB_POLL_INTERVAL_MS,
  JOB_STATUS,
  type JobStatus,
  type RegulationStatus,
} from '@/lib/utils/constants';

export interface Regulation {
  id: string;
  rule_id: string;
  jurisdiction: string;
  source_text: string;
  description: string | null;
  formal_logic: string;
  status: RegulationStatus;
  version: string;
  validation_message: string | null;
}

export interface RegulationJob {
  job_id: string;
  status: JobStatus;
  error: string | null;
}

export interface NewRegulation {
  section: string;
  content: string;
}

const REGULATIONS_KEY = ['regulations'] as const;

export function useRegulations() {
  return useQuery({
    queryKey: REGULATIONS_KEY,
    queryFn: async () => (await api.get<Regulation[]>('/regulations/')).data,
  });
}

export function useCreateRegulation() {
  return useMutation({
    mutationFn: async (body: NewRegulation) =>
      (await api.post<{ job_id: string }>('/regulations/', body)).data,
  });
}

export function useRegulationJob(jobId: string | null) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: ['regulation-job', jobId],
    enabled: jobId !== null,
    queryFn: async () => {
      const job = (await api.get<RegulationJob>(`/regulations/jobs/${jobId}`)).data;
      if (job.status !== JOB_STATUS.RUNNING) {
        await queryClient.invalidateQueries({ queryKey: REGULATIONS_KEY });
      }
      return job;
    },
    refetchInterval: (query) =>
      query.state.data?.status === JOB_STATUS.RUNNING || !query.state.data
        ? JOB_POLL_INTERVAL_MS
        : false,
  });
}

export function useApproveRegulation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) =>
      (await api.post<Regulation>(`/regulations/${id}/approve`)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: REGULATIONS_KEY }),
  });
}

export function useRejectRegulation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { id: string; reason?: string }) =>
      (await api.post<Regulation>(`/regulations/${vars.id}/reject`, {
        reason: vars.reason || null,
      })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: REGULATIONS_KEY }),
  });
}
